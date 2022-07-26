#!/bin/bash

CUDA_VERSION=11.0
WHEEL_TAG=manylinux2014_x86_64

echo "Build with CUDA ${CUDA_VERSION}"

if [[ -n $BUILDKITE_PULL_REQUEST && $BUILDKITE_PULL_REQUEST != "false" ]]
then
  is_pull_request=1
else
  is_pull_request=0
fi

if [[ $BUILDKITE_BRANCH == "master" || $BUILDKITE_BRANCH == "release_"* ]]
then
  is_release_branch=1
else
  is_release_branch=0
fi

if [[ $is_pull_request || ($is_release_branch == 0) ]]
then
  arch_flag="-DGPU_COMPUTE_VER=75"
fi

command_wrapper="tests/ci_build/ci_build.sh gpu_build_centos7 docker --build-arg "`
                `"CUDA_VERSION_ARG=$CUDA_VERSION"

$command_wrapper tests/ci_build/build_via_cmake.sh -DUSE_CUDA=ON -DUSE_NCCL=ON \
  -DUSE_OPENMP=ON -DHIDE_CXX_SYMBOLS=ON ${arch_flag}
$command_wrapper tests/ci_build/build_via_cmake.sh bash -c \
  "cd python-package && rm -rf dist/* && python setup.py bdist_wheel --universal"
$command_wrapper python tests/ci_build/rename_whl.py python-package/dist/*.whl \
  ${BUILDKITE_COMMIT} ${WHEEL_TAG}

tests/ci_build/ci_build.sh auditwheel_x86_64 docker auditwheel repair \
  --plat ${WHEEL_TAG} python-package/dist/*.whl
$command_wrapper python tests/ci_build/rename_whl.py wheelhouse/*.whl \
  ${BUILDKITE_COMMIT} ${WHEEL_TAG}
mv -v wheelhouse/*.whl python-package/dist/
# Make sure that libgomp.so is vendored in the wheel
tests/ci_build/ci_build.sh auditwheel_x86_64 docker bash -c \
  "unzip -l python-package/dist/*.whl | grep libgomp  || exit -1"
