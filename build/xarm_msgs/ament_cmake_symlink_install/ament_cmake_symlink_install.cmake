# generated from
# ament_cmake_core/cmake/symlink_install/ament_cmake_symlink_install.cmake.in

# create empty symlink install manifest before starting install step
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/symlink_install_manifest.txt")

#
# Reimplement CMake install(DIRECTORY) command to use symlinks instead of
# copying resources.
#
# :param cmake_current_source_dir: The CMAKE_CURRENT_SOURCE_DIR when install
#   was invoked
# :type cmake_current_source_dir: string
# :param ARGN: the same arguments as the CMake install command.
# :type ARGN: various
#
function(ament_cmake_symlink_install_directory cmake_current_source_dir)
  cmake_parse_arguments(ARG "OPTIONAL" "DESTINATION" "DIRECTORY;PATTERN;PATTERN_EXCLUDE" ${ARGN})
  if(ARG_UNPARSED_ARGUMENTS)
    message(FATAL_ERROR "ament_cmake_symlink_install_directory() called with "
      "unused/unsupported arguments: ${ARG_UNPARSED_ARGUMENTS}")
  endif()

  # make destination absolute path and ensure that it exists
  if(NOT IS_ABSOLUTE "${ARG_DESTINATION}")
    set(ARG_DESTINATION "/home/benongnuel/dev_ws/install/xarm_msgs/${ARG_DESTINATION}")
  endif()
  if(NOT EXISTS "${ARG_DESTINATION}")
    file(MAKE_DIRECTORY "${ARG_DESTINATION}")
  endif()

  # default pattern to include
  if(NOT ARG_PATTERN)
    set(ARG_PATTERN "*")
  endif()

  # iterate over directories
  foreach(dir ${ARG_DIRECTORY})
    # make dir an absolute path
    if(NOT IS_ABSOLUTE "${dir}")
      set(dir "${cmake_current_source_dir}/${dir}")
    endif()

    if(EXISTS "${dir}")
      # if directory has no trailing slash
      # append folder name to destination
      set(destination "${ARG_DESTINATION}")
      string(LENGTH "${dir}" length)
      math(EXPR offset "${length} - 1")
      string(SUBSTRING "${dir}" ${offset} 1 dir_last_char)
      if(NOT dir_last_char STREQUAL "/")
        get_filename_component(destination_name "${dir}" NAME)
        set(destination "${destination}/${destination_name}")
      else()
        # remove trailing slash
        string(SUBSTRING "${dir}" 0 ${offset} dir)
      endif()

      # glob recursive files
      set(relative_files "")
      foreach(pattern ${ARG_PATTERN})
        file(
          GLOB_RECURSE
          include_files
          RELATIVE "${dir}"
          "${dir}/${pattern}"
        )
        if(NOT include_files STREQUAL "")
          list(APPEND relative_files ${include_files})
        endif()
      endforeach()
      foreach(pattern ${ARG_PATTERN_EXCLUDE})
        file(
          GLOB_RECURSE
          exclude_files
          RELATIVE "${dir}"
          "${dir}/${pattern}"
        )
        if(NOT exclude_files STREQUAL "")
          list(REMOVE_ITEM relative_files ${exclude_files})
        endif()
      endforeach()
      list(SORT relative_files)

      foreach(relative_file ${relative_files})
        set(absolute_file "${dir}/${relative_file}")
        # determine link name for file including destination path
        set(symlink "${destination}/${relative_file}")

        # ensure that destination exists
        get_filename_component(symlink_dir "${symlink}" PATH)
        if(NOT EXISTS "${symlink_dir}")
          file(MAKE_DIRECTORY "${symlink_dir}")
        endif()

        _ament_cmake_symlink_install_create_symlink("${absolute_file}" "${symlink}")
      endforeach()
    else()
      if(NOT ARG_OPTIONAL)
        message(FATAL_ERROR
          "ament_cmake_symlink_install_directory() can't find '${dir}'")
      endif()
    endif()
  endforeach()
endfunction()

#
# Reimplement CMake install(FILES) command to use symlinks instead of copying
# resources.
#
# :param cmake_current_source_dir: The CMAKE_CURRENT_SOURCE_DIR when install
#   was invoked
# :type cmake_current_source_dir: string
# :param ARGN: the same arguments as the CMake install command.
# :type ARGN: various
#
function(ament_cmake_symlink_install_files cmake_current_source_dir)
  cmake_parse_arguments(ARG "OPTIONAL" "DESTINATION;RENAME" "FILES" ${ARGN})
  if(ARG_UNPARSED_ARGUMENTS)
    message(FATAL_ERROR "ament_cmake_symlink_install_files() called with "
      "unused/unsupported arguments: ${ARG_UNPARSED_ARGUMENTS}")
  endif()

  # make destination an absolute path and ensure that it exists
  if(NOT IS_ABSOLUTE "${ARG_DESTINATION}")
    set(ARG_DESTINATION "/home/benongnuel/dev_ws/install/xarm_msgs/${ARG_DESTINATION}")
  endif()
  if(NOT EXISTS "${ARG_DESTINATION}")
    file(MAKE_DIRECTORY "${ARG_DESTINATION}")
  endif()

  if(ARG_RENAME)
    list(LENGTH ARG_FILES file_count)
    if(NOT file_count EQUAL 1)
    message(FATAL_ERROR "ament_cmake_symlink_install_files() called with "
      "RENAME argument but not with a single file")
    endif()
  endif()

  # iterate over files
  foreach(file ${ARG_FILES})
    # make file an absolute path
    if(NOT IS_ABSOLUTE "${file}")
      set(file "${cmake_current_source_dir}/${file}")
    endif()

    if(EXISTS "${file}")
      # determine link name for file including destination path
      get_filename_component(filename "${file}" NAME)
      if(NOT ARG_RENAME)
        set(symlink "${ARG_DESTINATION}/${filename}")
      else()
        set(symlink "${ARG_DESTINATION}/${ARG_RENAME}")
      endif()
      _ament_cmake_symlink_install_create_symlink("${file}" "${symlink}")
    else()
      if(NOT ARG_OPTIONAL)
        message(FATAL_ERROR
          "ament_cmake_symlink_install_files() can't find '${file}'")
      endif()
    endif()
  endforeach()
endfunction()

#
# Reimplement CMake install(PROGRAMS) command to use symlinks instead of copying
# resources.
#
# :param cmake_current_source_dir: The CMAKE_CURRENT_SOURCE_DIR when install
#   was invoked
# :type cmake_current_source_dir: string
# :param ARGN: the same arguments as the CMake install command.
# :type ARGN: various
#
function(ament_cmake_symlink_install_programs cmake_current_source_dir)
  cmake_parse_arguments(ARG "OPTIONAL" "DESTINATION" "PROGRAMS" ${ARGN})
  if(ARG_UNPARSED_ARGUMENTS)
    message(FATAL_ERROR "ament_cmake_symlink_install_programs() called with "
      "unused/unsupported arguments: ${ARG_UNPARSED_ARGUMENTS}")
  endif()

  # make destination an absolute path and ensure that it exists
  if(NOT IS_ABSOLUTE "${ARG_DESTINATION}")
    set(ARG_DESTINATION "/home/benongnuel/dev_ws/install/xarm_msgs/${ARG_DESTINATION}")
  endif()
  if(NOT EXISTS "${ARG_DESTINATION}")
    file(MAKE_DIRECTORY "${ARG_DESTINATION}")
  endif()

  # iterate over programs
  foreach(file ${ARG_PROGRAMS})
    # make file an absolute path
    if(NOT IS_ABSOLUTE "${file}")
      set(file "${cmake_current_source_dir}/${file}")
    endif()

    if(EXISTS "${file}")
      # determine link name for file including destination path
      get_filename_component(filename "${file}" NAME)
      set(symlink "${ARG_DESTINATION}/${filename}")
      _ament_cmake_symlink_install_create_symlink("${file}" "${symlink}")
    else()
      if(NOT ARG_OPTIONAL)
        message(FATAL_ERROR
          "ament_cmake_symlink_install_programs() can't find '${file}'")
      endif()
    endif()
  endforeach()
endfunction()

#
# Reimplement CMake install(TARGETS) command to use symlinks instead of copying
# resources.
#
# :param TARGET_FILES: the absolute files, replacing the name of targets passed
#   in as TARGETS
# :type TARGET_FILES: list of files
# :param ARGN: the same arguments as the CMake install command except that
#   keywords identifying the kind of type and the DESTINATION keyword must be
#   joined with an underscore, e.g. ARCHIVE_DESTINATION.
# :type ARGN: various
#
function(ament_cmake_symlink_install_targets)
  cmake_parse_arguments(ARG "OPTIONAL" "ARCHIVE_DESTINATION;DESTINATION;LIBRARY_DESTINATION;RUNTIME_DESTINATION"
    "TARGETS;TARGET_FILES" ${ARGN})
  if(ARG_UNPARSED_ARGUMENTS)
    message(FATAL_ERROR "ament_cmake_symlink_install_targets() called with "
      "unused/unsupported arguments: ${ARG_UNPARSED_ARGUMENTS}")
  endif()

  # iterate over target files
  foreach(file ${ARG_TARGET_FILES})
    if(NOT IS_ABSOLUTE "${file}")
      message(FATAL_ERROR "ament_cmake_symlink_install_targets() target file "
        "'${file}' must be an absolute path")
    endif()

    # determine destination of file based on extension
    set(destination "")
    get_filename_component(fileext "${file}" EXT)
    if(fileext STREQUAL ".a" OR fileext STREQUAL ".lib")
      set(destination "${ARG_ARCHIVE_DESTINATION}")
    elseif(fileext STREQUAL ".dylib" OR fileext MATCHES "\\.so(\\.[0-9]+)?(\\.[0-9]+)?(\\.[0-9]+)?$")
      set(destination "${ARG_LIBRARY_DESTINATION}")
    elseif(fileext STREQUAL "" OR fileext STREQUAL ".dll" OR fileext STREQUAL ".exe")
      set(destination "${ARG_RUNTIME_DESTINATION}")
    endif()
    if(destination STREQUAL "")
      set(destination "${ARG_DESTINATION}")
    endif()

    # make destination an absolute path and ensure that it exists
    if(NOT IS_ABSOLUTE "${destination}")
      set(destination "/home/benongnuel/dev_ws/install/xarm_msgs/${destination}")
    endif()
    if(NOT EXISTS "${destination}")
      file(MAKE_DIRECTORY "${destination}")
    endif()

    if(EXISTS "${file}")
      # determine link name for file including destination path
      get_filename_component(filename "${file}" NAME)
      set(symlink "${destination}/${filename}")
      _ament_cmake_symlink_install_create_symlink("${file}" "${symlink}")
    else()
      if(NOT ARG_OPTIONAL)
        message(FATAL_ERROR
          "ament_cmake_symlink_install_targets() can't find '${file}'")
      endif()
    endif()
  endforeach()
endfunction()

function(_ament_cmake_symlink_install_create_symlink absolute_file symlink)
  # register symlink for being removed during install step
  file(APPEND "${CMAKE_CURRENT_BINARY_DIR}/symlink_install_manifest.txt"
    "${symlink}\n")

  # avoid any work if correct symlink is already in place
  if(EXISTS "${symlink}" AND IS_SYMLINK "${symlink}")
    get_filename_component(destination "${symlink}" REALPATH)
    get_filename_component(real_absolute_file "${absolute_file}" REALPATH)
    if(destination STREQUAL real_absolute_file)
      message(STATUS "Up-to-date symlink: ${symlink}")
      return()
    endif()
  endif()

  message(STATUS "Symlinking: ${symlink}")
  if(EXISTS "${symlink}" OR IS_SYMLINK "${symlink}")
    file(REMOVE "${symlink}")
  endif()

  execute_process(
    COMMAND "/usr/bin/cmake" "-E" "create_symlink"
      "${absolute_file}"
      "${symlink}"
  )
  # the CMake command does not provide a return code so check manually
  if(NOT EXISTS "${symlink}" OR NOT IS_SYMLINK "${symlink}")
    get_filename_component(destination "${symlink}" REALPATH)
    message(FATAL_ERROR
      "Could not create symlink '${symlink}' pointing to '${absolute_file}'")
  endif()
endfunction()

# end of template

message(STATUS "Execute custom install script")

# begin of custom install code

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_index/share/ament_index/resource_index/rosidl_interfaces/xarm_msgs" "DESTINATION" "share/ament_index/resource_index/rosidl_interfaces")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_index/share/ament_index/resource_index/rosidl_interfaces/xarm_msgs" "DESTINATION" "share/ament_index/resource_index/rosidl_interfaces")

# install(DIRECTORY "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_generator_c/xarm_msgs/" "DESTINATION" "include/xarm_msgs/xarm_msgs" "PATTERN" "*.h")
ament_cmake_symlink_install_directory("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" DIRECTORY "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_generator_c/xarm_msgs/" "DESTINATION" "include/xarm_msgs/xarm_msgs" "PATTERN" "*.h")

# install(FILES "/opt/ros/humble/lib/python3.10/site-packages/ament_package/template/environment_hook/library_path.sh" "DESTINATION" "share/xarm_msgs/environment")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/opt/ros/humble/lib/python3.10/site-packages/ament_package/template/environment_hook/library_path.sh" "DESTINATION" "share/xarm_msgs/environment")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_environment_hooks/library_path.dsv" "DESTINATION" "share/xarm_msgs/environment")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_environment_hooks/library_path.dsv" "DESTINATION" "share/xarm_msgs/environment")

# install(DIRECTORY "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_typesupport_fastrtps_c/xarm_msgs/" "DESTINATION" "include/xarm_msgs/xarm_msgs" "PATTERN_EXCLUDE" "*.cpp")
ament_cmake_symlink_install_directory("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" DIRECTORY "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_typesupport_fastrtps_c/xarm_msgs/" "DESTINATION" "include/xarm_msgs/xarm_msgs" "PATTERN_EXCLUDE" "*.cpp")

# install(DIRECTORY "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_generator_cpp/xarm_msgs/" "DESTINATION" "include/xarm_msgs/xarm_msgs" "PATTERN" "*.hpp")
ament_cmake_symlink_install_directory("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" DIRECTORY "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_generator_cpp/xarm_msgs/" "DESTINATION" "include/xarm_msgs/xarm_msgs" "PATTERN" "*.hpp")

# install(DIRECTORY "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_typesupport_fastrtps_cpp/xarm_msgs/" "DESTINATION" "include/xarm_msgs/xarm_msgs" "PATTERN_EXCLUDE" "*.cpp")
ament_cmake_symlink_install_directory("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" DIRECTORY "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_typesupport_fastrtps_cpp/xarm_msgs/" "DESTINATION" "include/xarm_msgs/xarm_msgs" "PATTERN_EXCLUDE" "*.cpp")

# install(DIRECTORY "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_typesupport_introspection_c/xarm_msgs/" "DESTINATION" "include/xarm_msgs/xarm_msgs" "PATTERN" "*.h")
ament_cmake_symlink_install_directory("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" DIRECTORY "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_typesupport_introspection_c/xarm_msgs/" "DESTINATION" "include/xarm_msgs/xarm_msgs" "PATTERN" "*.h")

# install(DIRECTORY "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_typesupport_introspection_cpp/xarm_msgs/" "DESTINATION" "include/xarm_msgs/xarm_msgs" "PATTERN" "*.hpp")
ament_cmake_symlink_install_directory("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" DIRECTORY "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_typesupport_introspection_cpp/xarm_msgs/" "DESTINATION" "include/xarm_msgs/xarm_msgs" "PATTERN" "*.hpp")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_environment_hooks/pythonpath.sh" "DESTINATION" "share/xarm_msgs/environment")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_environment_hooks/pythonpath.sh" "DESTINATION" "share/xarm_msgs/environment")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_environment_hooks/pythonpath.dsv" "DESTINATION" "share/xarm_msgs/environment")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_environment_hooks/pythonpath.dsv" "DESTINATION" "share/xarm_msgs/environment")

# install(DIRECTORY "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_python/xarm_msgs/xarm_msgs.egg-info/" "DESTINATION" "local/lib/python3.10/dist-packages/xarm_msgs-0.0.0-py3.10.egg-info")
ament_cmake_symlink_install_directory("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" DIRECTORY "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_python/xarm_msgs/xarm_msgs.egg-info/" "DESTINATION" "local/lib/python3.10/dist-packages/xarm_msgs-0.0.0-py3.10.egg-info")

# install(DIRECTORY "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_generator_py/xarm_msgs/" "DESTINATION" "local/lib/python3.10/dist-packages/xarm_msgs" "PATTERN_EXCLUDE" "*.pyc" "PATTERN_EXCLUDE" "__pycache__")
ament_cmake_symlink_install_directory("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" DIRECTORY "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_generator_py/xarm_msgs/" "DESTINATION" "local/lib/python3.10/dist-packages/xarm_msgs" "PATTERN_EXCLUDE" "*.pyc" "PATTERN_EXCLUDE" "__pycache__")

# install("TARGETS" "xarm_msgs__rosidl_typesupport_fastrtps_c__pyext" "DESTINATION" "local/lib/python3.10/dist-packages/xarm_msgs")
include("/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_symlink_install_targets_0_${CMAKE_INSTALL_CONFIG_NAME}.cmake")

# install("TARGETS" "xarm_msgs__rosidl_typesupport_introspection_c__pyext" "DESTINATION" "local/lib/python3.10/dist-packages/xarm_msgs")
include("/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_symlink_install_targets_1_${CMAKE_INSTALL_CONFIG_NAME}.cmake")

# install("TARGETS" "xarm_msgs__rosidl_typesupport_c__pyext" "DESTINATION" "local/lib/python3.10/dist-packages/xarm_msgs")
include("/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_symlink_install_targets_2_${CMAKE_INSTALL_CONFIG_NAME}.cmake")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/msg/RobotMsg.idl" "DESTINATION" "share/xarm_msgs/msg")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/msg/RobotMsg.idl" "DESTINATION" "share/xarm_msgs/msg")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/msg/IOState.idl" "DESTINATION" "share/xarm_msgs/msg")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/msg/IOState.idl" "DESTINATION" "share/xarm_msgs/msg")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/msg/CIOState.idl" "DESTINATION" "share/xarm_msgs/msg")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/msg/CIOState.idl" "DESTINATION" "share/xarm_msgs/msg")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/msg/MoveVelocity.idl" "DESTINATION" "share/xarm_msgs/msg")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/msg/MoveVelocity.idl" "DESTINATION" "share/xarm_msgs/msg")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/BioGripperCtrl.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/BioGripperCtrl.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/BioGripperEnable.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/BioGripperEnable.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/Call.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/Call.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/GetAnalogIO.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/GetAnalogIO.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/GetDigitalIO.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/GetDigitalIO.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/GetFloat32.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/GetFloat32.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/GetFloat32List.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/GetFloat32List.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/GetInt16.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/GetInt16.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/GetInt16List.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/GetInt16List.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/GetInt32.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/GetInt32.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/GetInt32ByType.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/GetInt32ByType.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/GetSetModbusData.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/GetSetModbusData.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/GripperMove.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/GripperMove.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/MoveCartesian.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/MoveCartesian.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/MoveCircle.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/MoveCircle.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/MoveHome.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/MoveHome.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/MoveJoint.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/MoveJoint.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/MoveVelocity.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/MoveVelocity.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/RobotiqActivate.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/RobotiqActivate.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/RobotiqGetStatus.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/RobotiqGetStatus.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/RobotiqMove.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/RobotiqMove.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/RobotiqReset.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/RobotiqReset.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/SetAnalogIO.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/SetAnalogIO.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/SetDigitalIO.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/SetDigitalIO.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/SetFloat32.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/SetFloat32.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/SetFloat32List.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/SetFloat32List.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/SetInt16.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/SetInt16.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/SetInt16ById.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/SetInt16ById.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/SetInt16List.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/SetInt16List.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/SetInt32.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/SetInt32.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/SetInt32ByType.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/SetInt32ByType.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/TrajCtrl.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/TrajCtrl.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/TrajPlay.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/TrajPlay.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/VacuumGripperCtrl.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/VacuumGripperCtrl.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/SetTcpLoad.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/SetTcpLoad.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/SetModbusTimeout.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/SetModbusTimeout.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/IdenLoad.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/IdenLoad.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/FtCaliLoad.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/FtCaliLoad.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/FtForceConfig.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/FtForceConfig.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/FtForcePid.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/FtForcePid.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/FtImpedance.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/FtImpedance.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/LinearTrackBackOrigin.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/LinearTrackBackOrigin.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/LinearTrackSetPos.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/LinearTrackSetPos.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/PlanExec.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/PlanExec.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/PlanJoint.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/PlanJoint.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/PlanPose.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/PlanPose.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/PlanSingleStraight.idl" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_adapter/xarm_msgs/srv/PlanSingleStraight.idl" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/msg/RobotMsg.msg" "DESTINATION" "share/xarm_msgs/msg")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/msg/RobotMsg.msg" "DESTINATION" "share/xarm_msgs/msg")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/msg/IOState.msg" "DESTINATION" "share/xarm_msgs/msg")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/msg/IOState.msg" "DESTINATION" "share/xarm_msgs/msg")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/msg/CIOState.msg" "DESTINATION" "share/xarm_msgs/msg")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/msg/CIOState.msg" "DESTINATION" "share/xarm_msgs/msg")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/msg/MoveVelocity.msg" "DESTINATION" "share/xarm_msgs/msg")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/msg/MoveVelocity.msg" "DESTINATION" "share/xarm_msgs/msg")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/BioGripperCtrl.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/BioGripperCtrl.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/BioGripperCtrl_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/BioGripperCtrl_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/BioGripperCtrl_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/BioGripperCtrl_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/BioGripperEnable.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/BioGripperEnable.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/BioGripperEnable_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/BioGripperEnable_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/BioGripperEnable_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/BioGripperEnable_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/Call.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/Call.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/Call_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/Call_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/Call_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/Call_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/GetAnalogIO.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/GetAnalogIO.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetAnalogIO_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetAnalogIO_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetAnalogIO_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetAnalogIO_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/GetDigitalIO.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/GetDigitalIO.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetDigitalIO_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetDigitalIO_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetDigitalIO_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetDigitalIO_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/GetFloat32.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/GetFloat32.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetFloat32_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetFloat32_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetFloat32_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetFloat32_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/GetFloat32List.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/GetFloat32List.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetFloat32List_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetFloat32List_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetFloat32List_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetFloat32List_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/GetInt16.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/GetInt16.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetInt16_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetInt16_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetInt16_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetInt16_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/GetInt16List.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/GetInt16List.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetInt16List_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetInt16List_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetInt16List_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetInt16List_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/GetInt32.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/GetInt32.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetInt32_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetInt32_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetInt32_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetInt32_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/GetInt32ByType.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/GetInt32ByType.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetInt32ByType_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetInt32ByType_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetInt32ByType_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetInt32ByType_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/GetSetModbusData.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/GetSetModbusData.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetSetModbusData_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetSetModbusData_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetSetModbusData_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GetSetModbusData_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/GripperMove.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/GripperMove.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GripperMove_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GripperMove_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GripperMove_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/GripperMove_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/MoveCartesian.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/MoveCartesian.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/MoveCartesian_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/MoveCartesian_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/MoveCartesian_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/MoveCartesian_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/MoveCircle.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/MoveCircle.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/MoveCircle_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/MoveCircle_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/MoveCircle_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/MoveCircle_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/MoveHome.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/MoveHome.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/MoveHome_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/MoveHome_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/MoveHome_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/MoveHome_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/MoveJoint.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/MoveJoint.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/MoveJoint_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/MoveJoint_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/MoveJoint_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/MoveJoint_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/MoveVelocity.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/MoveVelocity.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/MoveVelocity_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/MoveVelocity_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/MoveVelocity_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/MoveVelocity_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/RobotiqActivate.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/RobotiqActivate.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/RobotiqActivate_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/RobotiqActivate_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/RobotiqActivate_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/RobotiqActivate_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/RobotiqGetStatus.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/RobotiqGetStatus.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/RobotiqGetStatus_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/RobotiqGetStatus_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/RobotiqGetStatus_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/RobotiqGetStatus_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/RobotiqMove.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/RobotiqMove.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/RobotiqMove_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/RobotiqMove_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/RobotiqMove_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/RobotiqMove_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/RobotiqReset.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/RobotiqReset.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/RobotiqReset_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/RobotiqReset_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/RobotiqReset_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/RobotiqReset_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/SetAnalogIO.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/SetAnalogIO.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetAnalogIO_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetAnalogIO_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetAnalogIO_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetAnalogIO_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/SetDigitalIO.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/SetDigitalIO.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetDigitalIO_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetDigitalIO_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetDigitalIO_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetDigitalIO_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/SetFloat32.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/SetFloat32.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetFloat32_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetFloat32_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetFloat32_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetFloat32_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/SetFloat32List.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/SetFloat32List.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetFloat32List_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetFloat32List_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetFloat32List_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetFloat32List_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/SetInt16.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/SetInt16.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetInt16_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetInt16_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetInt16_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetInt16_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/SetInt16ById.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/SetInt16ById.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetInt16ById_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetInt16ById_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetInt16ById_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetInt16ById_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/SetInt16List.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/SetInt16List.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetInt16List_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetInt16List_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetInt16List_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetInt16List_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/SetInt32.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/SetInt32.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetInt32_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetInt32_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetInt32_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetInt32_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/SetInt32ByType.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/SetInt32ByType.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetInt32ByType_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetInt32ByType_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetInt32ByType_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetInt32ByType_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/TrajCtrl.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/TrajCtrl.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/TrajCtrl_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/TrajCtrl_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/TrajCtrl_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/TrajCtrl_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/TrajPlay.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/TrajPlay.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/TrajPlay_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/TrajPlay_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/TrajPlay_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/TrajPlay_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/VacuumGripperCtrl.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/VacuumGripperCtrl.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/VacuumGripperCtrl_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/VacuumGripperCtrl_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/VacuumGripperCtrl_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/VacuumGripperCtrl_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/SetTcpLoad.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/SetTcpLoad.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetTcpLoad_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetTcpLoad_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetTcpLoad_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetTcpLoad_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/SetModbusTimeout.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/SetModbusTimeout.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetModbusTimeout_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetModbusTimeout_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetModbusTimeout_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/SetModbusTimeout_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/IdenLoad.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/IdenLoad.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/IdenLoad_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/IdenLoad_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/IdenLoad_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/IdenLoad_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/FtCaliLoad.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/FtCaliLoad.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/FtCaliLoad_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/FtCaliLoad_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/FtCaliLoad_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/FtCaliLoad_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/FtForceConfig.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/FtForceConfig.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/FtForceConfig_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/FtForceConfig_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/FtForceConfig_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/FtForceConfig_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/FtForcePid.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/FtForcePid.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/FtForcePid_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/FtForcePid_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/FtForcePid_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/FtForcePid_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/FtImpedance.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/FtImpedance.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/FtImpedance_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/FtImpedance_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/FtImpedance_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/FtImpedance_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/LinearTrackBackOrigin.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/LinearTrackBackOrigin.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/LinearTrackBackOrigin_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/LinearTrackBackOrigin_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/LinearTrackBackOrigin_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/LinearTrackBackOrigin_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/LinearTrackSetPos.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/LinearTrackSetPos.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/LinearTrackSetPos_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/LinearTrackSetPos_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/LinearTrackSetPos_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/LinearTrackSetPos_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/PlanExec.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/PlanExec.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/PlanExec_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/PlanExec_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/PlanExec_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/PlanExec_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/PlanJoint.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/PlanJoint.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/PlanJoint_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/PlanJoint_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/PlanJoint_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/PlanJoint_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/PlanPose.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/PlanPose.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/PlanPose_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/PlanPose_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/PlanPose_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/PlanPose_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/PlanSingleStraight.srv" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/srv/PlanSingleStraight.srv" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/PlanSingleStraight_Request.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/PlanSingleStraight_Request.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/PlanSingleStraight_Response.msg" "DESTINATION" "share/xarm_msgs/srv")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/srv/PlanSingleStraight_Response.msg" "DESTINATION" "share/xarm_msgs/srv")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_index/share/ament_index/resource_index/package_run_dependencies/xarm_msgs" "DESTINATION" "share/ament_index/resource_index/package_run_dependencies")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_index/share/ament_index/resource_index/package_run_dependencies/xarm_msgs" "DESTINATION" "share/ament_index/resource_index/package_run_dependencies")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_index/share/ament_index/resource_index/parent_prefix_path/xarm_msgs" "DESTINATION" "share/ament_index/resource_index/parent_prefix_path")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_index/share/ament_index/resource_index/parent_prefix_path/xarm_msgs" "DESTINATION" "share/ament_index/resource_index/parent_prefix_path")

# install(FILES "/opt/ros/humble/share/ament_cmake_core/cmake/environment_hooks/environment/ament_prefix_path.sh" "DESTINATION" "share/xarm_msgs/environment")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/opt/ros/humble/share/ament_cmake_core/cmake/environment_hooks/environment/ament_prefix_path.sh" "DESTINATION" "share/xarm_msgs/environment")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_environment_hooks/ament_prefix_path.dsv" "DESTINATION" "share/xarm_msgs/environment")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_environment_hooks/ament_prefix_path.dsv" "DESTINATION" "share/xarm_msgs/environment")

# install(FILES "/opt/ros/humble/share/ament_cmake_core/cmake/environment_hooks/environment/path.sh" "DESTINATION" "share/xarm_msgs/environment")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/opt/ros/humble/share/ament_cmake_core/cmake/environment_hooks/environment/path.sh" "DESTINATION" "share/xarm_msgs/environment")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_environment_hooks/path.dsv" "DESTINATION" "share/xarm_msgs/environment")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_environment_hooks/path.dsv" "DESTINATION" "share/xarm_msgs/environment")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_environment_hooks/local_setup.bash" "DESTINATION" "share/xarm_msgs")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_environment_hooks/local_setup.bash" "DESTINATION" "share/xarm_msgs")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_environment_hooks/local_setup.sh" "DESTINATION" "share/xarm_msgs")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_environment_hooks/local_setup.sh" "DESTINATION" "share/xarm_msgs")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_environment_hooks/local_setup.zsh" "DESTINATION" "share/xarm_msgs")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_environment_hooks/local_setup.zsh" "DESTINATION" "share/xarm_msgs")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_environment_hooks/local_setup.dsv" "DESTINATION" "share/xarm_msgs")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_environment_hooks/local_setup.dsv" "DESTINATION" "share/xarm_msgs")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_environment_hooks/package.dsv" "DESTINATION" "share/xarm_msgs")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_environment_hooks/package.dsv" "DESTINATION" "share/xarm_msgs")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_index/share/ament_index/resource_index/packages/xarm_msgs" "DESTINATION" "share/ament_index/resource_index/packages")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_index/share/ament_index/resource_index/packages/xarm_msgs" "DESTINATION" "share/ament_index/resource_index/packages")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/rosidl_cmake-extras.cmake" "DESTINATION" "share/xarm_msgs/cmake")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/rosidl_cmake-extras.cmake" "DESTINATION" "share/xarm_msgs/cmake")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_export_dependencies/ament_cmake_export_dependencies-extras.cmake" "DESTINATION" "share/xarm_msgs/cmake")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_export_dependencies/ament_cmake_export_dependencies-extras.cmake" "DESTINATION" "share/xarm_msgs/cmake")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_export_include_directories/ament_cmake_export_include_directories-extras.cmake" "DESTINATION" "share/xarm_msgs/cmake")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_export_include_directories/ament_cmake_export_include_directories-extras.cmake" "DESTINATION" "share/xarm_msgs/cmake")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_export_libraries/ament_cmake_export_libraries-extras.cmake" "DESTINATION" "share/xarm_msgs/cmake")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_export_libraries/ament_cmake_export_libraries-extras.cmake" "DESTINATION" "share/xarm_msgs/cmake")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_export_targets/ament_cmake_export_targets-extras.cmake" "DESTINATION" "share/xarm_msgs/cmake")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_export_targets/ament_cmake_export_targets-extras.cmake" "DESTINATION" "share/xarm_msgs/cmake")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/rosidl_cmake_export_typesupport_targets-extras.cmake" "DESTINATION" "share/xarm_msgs/cmake")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/rosidl_cmake_export_typesupport_targets-extras.cmake" "DESTINATION" "share/xarm_msgs/cmake")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/rosidl_cmake_export_typesupport_libraries-extras.cmake" "DESTINATION" "share/xarm_msgs/cmake")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/rosidl_cmake/rosidl_cmake_export_typesupport_libraries-extras.cmake" "DESTINATION" "share/xarm_msgs/cmake")

# install(FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_core/xarm_msgsConfig.cmake" "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_core/xarm_msgsConfig-version.cmake" "DESTINATION" "share/xarm_msgs/cmake")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_core/xarm_msgsConfig.cmake" "/home/benongnuel/dev_ws/build/xarm_msgs/ament_cmake_core/xarm_msgsConfig-version.cmake" "DESTINATION" "share/xarm_msgs/cmake")

# install(FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/package.xml" "DESTINATION" "share/xarm_msgs")
ament_cmake_symlink_install_files("/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs" FILES "/home/benongnuel/dev_ws/src/xarm_ros2/xarm_msgs/package.xml" "DESTINATION" "share/xarm_msgs")
