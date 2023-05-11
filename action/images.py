# Copyright 2022-2023 Antmicro Ltd.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from common import run_cmd, get_file
from os import walk as os_walk, path as os_path, makedirs as os_makedirs, getcwd as os_getcwd
from subprocess import run, DEVNULL, CalledProcessError
from sys import exit as sys_exit
from dataclasses import dataclass
from tarfile import open as tarfile_open
from shutil import copytree
from pexpect import spawn as px_spawn, TIMEOUT as px_TIMEOUT


CR = r'\r'


@dataclass
class shared_directories_action:
    host: str
    target: str


shared_directories_actions: list[shared_directories_action] = []


def prepare_shared_directories(shared_directories: str):
    """
    Creates list of directories to share

    Parameters
    ----------
    shared_directories: str
        list of directories that the user wanted to share with emulated Linux
    """

    global shared_directories_actions

    shared_directories: list[list[str]] = [directory.split(' ') for directory in shared_directories.split('\n')]

    for directory in shared_directories:
        if len(directory) == 1 and directory[0] != '':
            shared_directories_actions.append(
                shared_directories_action(
                    directory[0],
                    '/home',
                )
            )
        elif len(directory) > 1:
            shared_directories_actions.append(
                shared_directories_action(
                    directory[0],
                    directory[1],
                )
            )


def prepare_kernel_and_initramfs(kernel: str):
    """
    Get the kernel package (kernel + initramfs + bootlader + firmware) and extract kernel and device tree from cpio archive.

    Parameters
    ----------
    kernel: str
        path or URL to the kernel package
    """

    get_file(kernel, "kernel.tar.xz")

    os_makedirs("images")

    with tarfile_open("kernel.tar.xz") as tar:
        tar.extractall("images")

    child = px_spawn(f'sh -c "cd {os_getcwd()};exec /bin/sh"', encoding="utf-8", timeout=10)

    try:
        child.expect_exact('#')
        child.sendline('')

        run_cmd(child, "#", "mkdir -p images/initramfs")
        run_cmd(child, "#", "cd images/initramfs && cpio -iv < ../rootfs.cpio")
        run_cmd(child, "#", f"cd {os_getcwd()}")
        run_cmd(child, "#", "cp images/initramfs/boot/Image images")
        run_cmd(child, "#", "cp images/initramfs/boot/*.dtb images")
        run_cmd(child, "#", "rm -rf images/initramfs")

        child.expect_exact('#')
    except px_TIMEOUT:
        sys_exit(1)


def burn_rootfs_image(
        user_directory: str,
        image: str,
        image_size: str,
        image_type: str):
    """
    Get the rootfs image, copy the user-selected data to the appropriate paths and creates a rootfs image to mount on the renode machine.
    Function copies all files specified by the user or required by other functions. When creating the image fails,
    it exits from the script with the same error code as failing command.

    Parameters
    ----------
    user_directory: str
        absolute path to action user catalog
    image:
        path or URL to the image
    image_size: str
        size of the rootfs in a format used by tools like truncate or auto to be calculated automatically
    image_type: str
        type of the image supported by action native or docker
    """

    if image_type == "native":
        get_file(image, "rootfs.tar.xz")
    elif image_type == "docker":
        print("Docker images are not yet supported")
        sys_exit(1)
    else:
        print(f"invalid image type: {image_type}")
        sys_exit(1)

    os_makedirs("images/rootfs/home")

    with tarfile_open("rootfs.tar.xz") as tar:
        tar.extractall("images/rootfs")

    for dir in shared_directories_actions:
        os_makedirs(f"images/rootfs/{dir.target}", exist_ok=True)
        copytree(
            f"{user_directory}/{dir.host}" if not dir.host.startswith('/') else dir.host,
            f"images/rootfs/{dir.target}",
            dirs_exist_ok=True
        )

    if image_size == "auto":
        size = 0
        for path, _, files in os_walk("images/rootfs"):
            for f in files:
                fp = os_path.join(path, f)
                if not os_path.islink(fp):
                    size += os_path.getsize(fp)

        image_size = f'{max(size * 2, 5 * 10**7)}'
    try:

        run(["truncate", "images/rootfs.img", "-s", image_size], check=True)
        run(["mkfs.ext4", "-d", "images/rootfs", "images/rootfs.img"],
            check=True,
            stdout=DEVNULL)
    except CalledProcessError as e:
        sys_exit(e.returncode)