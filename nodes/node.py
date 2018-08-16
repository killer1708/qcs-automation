#!/usr/bin/env python
"""
node.py:
"""

# from python lib
from abc import ABCMeta, abstractmethod

# from qcs automation libs
from libs.ssh_lib import SshConn
from libs.log.logger import Log

# create log object
log = Log()


class Node(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def deploy(self, pkg):
        pass

    @abstractmethod
    def walk(self, dir):
        pass

    @abstractmethod
    def is_path_exists(self, path):
        pass

    @abstractmethod
    def makedir(self, dir):
        pass

    @abstractmethod
    def restart(self):
        pass


class Linux(Node):

    def __init__(self, ip, user, password):
        self.ip = ip
        self.user = user
        self.password = password
        self.conn = SshConn(self.ip, self.user, self.password)
        self.host_type = 'linux'
        self.disks = list()
        self.mount_locations = list()

    def __str__(self):
        return "{}".format(self.conn.ip_address)

    @staticmethod
    def path_separator():
        return "/"

    def _get_disk_list(self):
        disks = list()
        # issue lsscsi to list all devices
        cmd = "lsscsi | awk '{print $NF}'"
        status, lsscsi_out, stderr = self.conn.execute_command(cmd)

        # skip boot and cdrom drive
        cmd = "mount | grep -i boot | awk '{print $1}'"
        status, stdout, stderr = self.conn.execute_command(cmd)
        skip_disks = [stdout[0][:-1], '/dev/sr0', '/dev/sr1', '/dev/sr2']

        # collect useful disks
        for disk in lsscsi_out:
            if disk in skip_disks:
                continue
            else:
                disks.append(disk)
        # return available disks
        return disks

    def refresh_disk_list(self):
        self.disks = self._get_disk_list()

    def change_hostname(self):
        new_name = "slave_{}".format(str(self).split('.')[-1])
        cmd = "hostnamectl set-hostname {}".format(new_name)
        status, stdout, stderr = self.conn.execute_command(cmd)
        if status:
            log.info(stdout)
            log.error(error)

    @property
    def disk_list(self):
        """
        get host available disk list
        """
        return self.disks

    def add_disk(self):
        pass

    def deploy(self, pkg):
        cmd = ['yum', 'install', pkg, '-y']
        self.conn.execute_command(cmd)

    def walk(self, dir_name):
        dir_queue = [dir_name]
        while len(dir_queue):
            _dir = dir_queue.pop()
            sub_dir = []
            files = []
            _, ls_lrt, error = self.conn.execute_command(['ls', '-lrt', _dir])
            if not error:
                # 1st entry would be count of dir and files in given folder
                ls_lrt = ls_lrt[1:]
                for entry in ls_lrt:
                    if entry.startswith("d"):
                        sub_dir.append(entry.split()[-1])
                        dir_queue.append('{}/{}'.format(_dir, entry.split()[-1]))
                    else:
                        files.append(entry.split()[-1])
                yield (_dir, sub_dir, files)

    def is_path_exists(self, path):
        _, _, error = self.conn.execute_command(['ls', path])
        if error:
            return False
        else:
            return True

    def makedir(self, dir_name):
        self.conn.execute_command(['mkdir', '-p', dir_name])

    def restart(self):
        raise NotImplementedError

    def create_file_system_on_disks(self):
        """
        Create file system on all avaliable disks
        :return None
        """
        self.filesystem_locations = list()
        for disk in self.disks:
            # Check if disk is already partinoned
            cmd = "parted -l | grep Error"
            _, _, stderr = self.conn.execute_command(cmd)
            for line in stderr:
                if disk in line:
                    log.info("Disk {} is not partioned.".format(disk))
                    break
            else:
                log.error("Disk {} already have partitons on it.".format(disk))

            # choose the partitioning standard
            cmd = "parted {} mklabel gpt".format(disk)
            _, _, _ = self.conn.execute_command(cmd)

            # partition the disk
            cmd = "parted -a opt {} mkpart primary ext4 0% 100%".format(disk)
            status, stdout, stderr = self.conn.execute_command(cmd)
            if status:
                log.info(stdout)
                raise Exception("Unable to create ext4 partition on disk {}"\
                                .format(disk))

            # get the partition
            cmd = "lsblk -l -oNAME {}".format(disk)
            _, stdout, _ = self.conn.execute_command(cmd)

            # remove header and device name
            stdout.pop(0)
            stdout.pop(0)
            partition_name = "/dev/{}".format(stdout[0])

            # create file system on disk
            cmd = "mkfs.ext4 -L Data {}".format(partition_name)
            status, stdout, _ = self.conn.execute_command(cmd)
            if status:
                log.info(stdout)
                raise Exception("Unable to create file system on partition {}"\
                                .format(partition_name))
            # append to available file system list
            self.filesystem_locations.append(partition_name)


if __name__ == '__main__':
    ln = Linux('192.168.102.14', 'root', 'master#123')
    print ({}.format(ln.is_path_exists('/root/test/wer')))

    # for _dir, sub_dirs, files in ln.walk('/root/test'):
    #     print _dir, sub_dirs, files
