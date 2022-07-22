import argparse
import copy

import boto3

from metadata import AMI_ID, COMMON_STACK_PARAMS, STACK_PARAMS

TEMPLATE_URL = "https://s3.amazonaws.com/buildkite-aws-stack/latest/aws-stack.yml"


def format_params(args, *, stack_id):
    params = copy.deepcopy(STACK_PARAMS[stack_id])
    params["ImageId"] = AMI_ID[stack_id][args.aws_region]
    params["BuildkiteQueue"] = stack_id
    params["CostAllocationTagValue"] = f"buildkite-{stack_id}"
    params["BuildkiteAgentToken"] = args.agent_token
    params.update(COMMON_STACK_PARAMS)
    return [{"ParameterKey": k, "ParameterValue": v} for k, v in params.items()]


def get_full_stack_id(stack_id):
    return f"buildkite-{stack_id}-autoscaling-group"


def main(args):
    client = boto3.client("cloudformation", region_name=args.aws_region)

    for stack_id in AMI_ID:
        stack_id_full = get_full_stack_id(stack_id)
        print(f"Creating elastic CI stack {stack_id_full}...")

        params = format_params(args, stack_id=stack_id)

        response = client.create_stack(
            StackName=stack_id_full,
            TemplateURL=TEMPLATE_URL,
            Capabilities=[
                "CAPABILITY_IAM",
                "CAPABILITY_NAMED_IAM",
                "CAPABILITY_AUTO_EXPAND",
            ],
            OnFailure="ROLLBACK",
            EnableTerminationProtection=False,
            Parameters=params,
        )
        print(f"CI stack {stack_id_full} is in progress in the background")

    for stack_id in AMI_ID:
        stack_id_full = get_full_stack_id(stack_id)
        waiter = client.get_waiter("stack_create_complete")
        waiter.wait(StackName=stack_id_full)
        print(f"CI stack {stack_id_full} is now finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--aws-region", type=str, required=True)
    parser.add_argument("--agent-token", type=str, required=True)
    args = parser.parse_args()
    main(args)
