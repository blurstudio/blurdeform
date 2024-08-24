project('blurdeform', 'cpp', default_options: ['cpp_std=c++20'])

maya_dep = dependency('maya')
maya_name_suffix = maya_dep.get_variable('name_suffix')
maya_version = maya_dep.get_variable('maya_version')

source_files = files([
  'src/blurPostDeformCmd.cpp',
  'src/blurPostDeformNode.cpp',
  'src/blurPostDeformPlugin.cpp',
  'src/common.cpp',
])

# If a user-built version file exists, then just use that
# Otherwise grab the latest tag from git
fs = import('fs')
if fs.is_file('src/version.h')
  message('Using existing version.h')
else
  git = find_program('git', native: true, required: true)
  version_h = vcs_tag(
    command: [git, 'describe', '--tags', '--match', 'v[0-9]*', '--dirty=+'],
    fallback: 'v0.0.1',
    input: 'src/version.h.in',
    output: 'version.h',
  )
  source_files = source_files + version_h
endif

cc = meson.get_compiler('cpp')
if cc.get_argument_syntax() == 'gcc'
  avx = ['-mavx', '-mfma']
else
  avx = ['/arch:AVX']
endif
add_project_arguments(avx, language: 'cpp')


outlib = shared_library(
  meson.project_name(),
  source_files,
  install: true,
  install_dir : meson.global_source_root() / 'output_Maya' + maya_version,
  include_directories : include_directories(['include']),
  dependencies : maya_dep,
  name_prefix : '',
  name_suffix : maya_name_suffix,
)
