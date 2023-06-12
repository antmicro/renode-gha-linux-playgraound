# renode-linux-runner-action

Copyright (c) 2022-2023 [Antmicro](https://www.antmicro.com)

This action enables users automatically test your projects that require certain Linux [devices](#devices) enabled, such as Video4Linux. Because we know that each project has very different configuration and ways to run it, we want to prepare an environment that's as configurable as possible.

Using the default configuration, you can enable the devices you want and run commands and scripts in a real Linux system that runs inside [Renode](https://renode.io/).

> **Warning**
> This action is under heavy development. We will do our best to avoid breaking
> changes, but we cannot guarantee full backwards compatibility at this point.
> We recommend using the `v0` tag to minimize chances of breakage. If your
> workflow fails due to our changes, feel free to file an issue.

## Parameters

### Tests configuration

- [`renode-run`](#running-your-commands-in-emulated-linux) - A command, list or [yaml Task](#tasks) with commands to run in Renode.
- [`shared-dirs`](#shared-directories) - Shared directory paths. The contents of these directories will be mounted in Renode.
- [`python-packages`](#python-packages) - Python packages from PyPI library or git repository that will be sideloaded into emulated Linux.
- [`repos`](#git-repositories) - git repositories that will be sideloaded into emulated Linux.
- [`fail-fast`](#fail-fast) - Fail after first non zero exit code instead of fail on the end. Default: true

### OS configuration

- [`rootfs-size`](#rootfs-size) - Set size of the rootfs image. Default: auto
- [`image-type`](#image) - native or docker. Read about the differences in the [image section](#image)
- [`image`](#image) - URL of the path to tar.xz archive with linux rootfs for the specified architecture or docker image identifier. If not specified, the action will use the default one. See releases for examples.
- [`tasks`](#tasks) - Allows you to change the way the system is initialized. See [Tasks](#tasks) for more details.

### Board and devices configuration

- [`network`](#network) - Turn on the Internet in the emulated Linux? Default: true
- [`devices`](#devices) - List of devices to add to the workflow. If not specified, the action will not install any devices.
- [`kernel`](#kernel) - URL of the path to the tar.xz archive containing the compiled embedded linux kernel + initramfs. If not specified, the action will use the default. See releases for examples.
- [`arch`](#emulation) - Processor architecture
- [`board`](#board) - A specific board name, or `default` for architecture default, or `custom` for a custom board
- [`resc`](#board) - Custom Renode script
- [`repl`](#board) - Custom Renode platform description

## Running your commands in emulated linux

This is the simplest example of running your commands in emulated Linux. The default image will boot and log itself into a basic shell session.

```yaml
- uses: antmicro/renode-linux-runner-action@v0
  with:
    renode-run: uname -a
```

This is the result:

```raw
# uname -a
Linux buildroot 5.10.178 #1 SMP Thu May 11 13:44:01 UTC 2023 riscv64 GNU/Linux
#
```

If you want to run more than one command, you can use a multiline string. For example, for this configuration:

```yaml
- uses: antmicro/renode-linux-runner-action@v0
  with:
    renode-run: |
      ls /dev | grep tty | head -n 3
      tty
```

the result is:

```raw
# ls /dev | grep tty | head -n 3
tty
tty0
tty1
# tty
/dev/ttySIF0
```

Of course, you can also run shell scripts, but you have to load them into the emulated system first using the [shared directories feature](#shared-directories) or by [sideloading git repositories](#git-repositories).

```yaml
- uses: antmicro/renode-linux-runner-action@v0
  with:
    shared-dirs: scripts
    renode-run: sh my-script.sh
```

You can also set additional test parameters with [task format](#tasks). For example:

```yaml
- uses: antmicro/renode-linux-runner-action@v0
  with:
    network: false
    renode-run: |
      - should-fail: true
      - commands:
        - "wget example.org"
```

This test will complete successfully because the network will be disabled in the test environment and wget will return a non-zero exit code.

### Special cases

If the action detects that one of your commands has failed, it will also fail with the error code that your command failed with, and no further commands will be executed. This behavior can be changed with the [`fail-fast`](#fail-fast) action parameter.

### Limitations

Because we wanted the system image to be very small, there is no standard `bash` shell, but a `busybox ash` shell instead. Some of your scripts may not work the same or work differently. If you really want `bash`, you can provide your own custom image. More on this [here](#image).

## Examples

The [release](.github/workflows/release.yml) workflow contains an example usage of this action.

## Emulation

The Linux emulation runs on the RISC-V/HiFive Unleashed single core platform in [Renode 1.13.3](https://github.com/renode/renode). This emulated system has some basics like 8GB of RAM and network connection configured.

### Architecture

Currently, the only supported architecture of the emulated system is RISC-V. You can specify the architecture with the `arch` parameter:

```yaml
- uses: antmicro/renode-linux-runner-action@v0
  with:
    arch: riscv64
    renode-run: ...
```

We are working on `arm64` support.

## Shared directories

You can specify many directories that will be added to the rootfs. All files from these directories will be available in the specified target directories.

In the following example, files from the `project-files` directory will be extracted to the `/opt/project` directory. If no destination directory is specified, the files will be extracted to `/home`.

```yaml
- uses: antmicro/renode-linux-runner-action@v0
  with:
    shared-dirs: |
      shared-dir1
      shared-dir2
      project-files /opt/project
    renode-run: command_to_run
```

## Devices

The action allows you to add additional devices that are available in a given kernel configuration. For example, if you want to add a stub Video4Linux device you can specify:

```yaml
- uses: antmicro/renode-linux-runner-action@v0
  with:
    shared-dirs: |
      scripts
      project-files /opt/project
    renode-run: ./build.sh
    devices: vivid
```

More about available devices and syntax to customize them can be found [here](docs/Devices.md).

## Python packages

This action offers sideloading Python packages that you want to use in the emulated system. You can select any package from PyPI or from a Git repository.

For example:

```yaml
- uses: antmicro/renode-linux-runner-action@v0
  with:
    renode-run: python --version
    python-packages: |
      git+https://github.com/antmicro/pyrav4l2.git
      pytest==5.3.0
```

The action will download all selected packages and their dependencies and install them later in the emulated Linux environment.

You can read about the details of how the action collects dependencies and installs them [here](docs/Python-packages.md).

## Git repositories

If you want to clone other Git repositories to the emulated system, you can use the `repos` argument. You can also specify the path into which you want to clone the repository:

```yaml
- uses: antmicro/renode-linux-runner-action@v0
  with:
    shared-dir: ./shared-dir
    renode-run: python --version
    repos: https://github.com/antmicro/pyrav4l2.git /path/to/repo
```

## Fail fast

By default, execution of the script is aborted on the first failure and an error code is returned. When this option is disabled, the last non zero exit code is returned after all commands are executed.

```yaml
- uses: antmicro/renode-linux-runner-action@v0
  with:
    fail-fast: false
    renode-run:
      gryp --version # fail gryp is not available
      grep --version # will be executed
```

## Network

You can disable networking in the emulated Linux by passing the `network: false` argument to the action

```yaml
- uses: antmicro/renode-linux-runner-action@v0
  with:
    shared-dir: ./shared-dir
    renode-run: python --version
    network: false
```

This can be useful when running the action in a container matrix strategy if you do not have permission to create `tap` interfaces.

More information about the network can be found [here](docs/Network.md).

## Image

If you need additional software, you can mount your own filesystem. More information on how it works can be found [here](docs/Image.md).

## Rootfs size

The size of the mounted rootfs can be specified with the `rootfs-size` parameter. The parameter accepts the sizes in bytes (i.e. `1000000000`), kilobytes (i.e. `50000K`), megabytes (i.e. `512M`) or gigabytes (i.e. `1G`). The default `rootfs-size` value is `auto`; with this setting the size is calculated automatically.

```yaml
- uses: antmicro/renode-linux-runner-action@v0
  with:
    shared-dir: shared-dir
    renode-run: python --version
    rootfs-size: 512M
```

## Tasks

Sometimes, after replacing the initramfs or board configuration, you may need to change the default commands that the action executes on each run. You can use the 'Task' mechanism. All the commands that the action executes are stored in the task files in `action/tasks/*.yml`. If you want to change any of these, you can pass your own task through the `tasks` action argument. If your task has the same name as one of the default ones, it will replace it.

For example:

```yaml
- uses: antmicro/renode-linux-runner-action@v0
  with:
    shared-dir: shared-dir
    renode-run: |
      command1
      command2
    tasks: |
      path/to/task/1
      https://task2/
```

### Task syntax

A task file is a YAML file with the following fields:

- `name`: the only mandatory field; it is used to resolve dependencies between tasks.
- `shell`: the name of the shell on which the commands will be executed. The action has three available shells (`host`, `target`, `renode`).
- `requires`: the array of tasks that must be executed before this task. This list is empty by default.
- `required-by`: the array of tasks that must be executed after this task. This list is empty by default.
- `echo`: Boolean parameter. If true, the output from the shell will be printed. Default: false
- `timeout`: Default timeout for each command. Commands can override this setting. Default: null, meaning no timeout for your commands.
- `fail-fast`: Boolean parameter. If true, the action will return the error from the first failed command and stop. Otherwise, the action will fail at the end of the task. Default: true
- `sleep`: The action will wait for the specified time in seconds before proceeding to the next task. Default: 0
- `command`: List of commands or `Command` objects to execute. Default: empty
- `vars`: Dictionary of variables. [Read more about it here](#variables). Default: empty

For example:

```yaml
name: task1
shell: target
requires: [renode_config]
echo: true
timeout: 5
fail-fast: true
commands:
  - expect:
    - "buildroot login:"
    timeout: null
    check-exit-code: false
  - "root"
  - "dmesg -n 1"
  - "date -s \"${{NOW}}\""
  - "echo ${{VAR1}}"
vars:
  VAR1: "hello, world!"
```

### Command syntax

For a list of commands you can just use a list of strings, but if you want more powerful customization, you can use a `Command` object with the following fields:

- `command`: A list of different shell commands. The shell command will be selected based of the index of expected string that was matched in the previous command. This allows you to react in different ways to different command results.
- `expect`: A list of strings. The action will wait for one of the strings and pass its index to the next command.
- `timeout`: Timeout in seconds for the command. By default, the timeout is inherited from the task.
- `echo`: Boolean parameter. If true, the output from the shell is printed. By default this parameter is inherited from the task.
- `check-exit-code`: Boolean parameter. If true, the shell will check whether the command failed or not. Default: true

### Variables

You can define a list of variables and use it later with `${{VAR_NAME}}`. In addition, some predefined global variables are available:

- `${{BOARD}}`: name of the selected board
- `${{NOW}}`: current date and time in the format `%Y-%m-%d %H:%M:%S`

### Shell initialization

All tasks that refer to a particular shell have an additional hidden dependency. They require the task that has the same name as the shell (for example, `renode`). These tasks are used to configure the shell. However, you can replace each one by simply using its name in your task.

## Kernel

It is possible to replace the Linux image on which the tests are run and mount the [file system image](#image). More information on how to do it can be found [in the 'Kernel' section of the docs](docs/Kernel.md).

## Board

The action allows you to select your own board and choose its configuration. You can select a board from the list (remember that you also need to select the matching processor architecture). Here are the available boards:

- [riscv64 - hifive_unleashed](action/device/hifive_unleashed/init.resc)

You can also choose the default board: `default` or your own board: `custom`. In the latter case, you have to provide your own resc and repl files, which will configure the emulation. Configuration files can be selected using [`resc`](https://renode.readthedocs.io/en/latest/introduction/using.html#resc-scripts) and [`repl`](https://renode.readthedocs.io/en/latest/advanced/platform_description_format.html) parameters. You can read more about these files in the [Renode documentation](https://renode.readthedocs.io/en/latest/index.html).
