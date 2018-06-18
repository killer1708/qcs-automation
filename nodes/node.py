from abc import ABCMeta, abstractmethod

from libs.ssh_lib import SshConn


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
        self.ssh_conn = SshConn(ip, user, password)

    @staticmethod
    def path_seperator():
        return "/"

    def deploy(self, pkg):
        cmd = ['yum', 'install', pkg, '-y']
        self.ssh_conn.execute_command(cmd)

    def walk(self, dir_name):
        dir_queue = [dir_name]
        while len(dir_queue):
            _dir = dir_queue.pop()
            sub_dir = []
            files = []
            _, ls_lrt, error = self.ssh_conn.execute_command(['ls', '-lrt', _dir])
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
        _, _, error = self.ssh_conn.execute_command(['ls', path])
        if error:
            return False
        else:
            return True

    def makedir(self, dir_name):
        self.ssh_conn.execute_command(['mkdir', '-p', dir_name])

    def restart(self):
        raise NotImplementedError


if __name__ == '__main__':
    ln = Linux('192.168.102.14', 'root', 'master#123')
    print ({}.format(ln.is_path_exists('/root/test/wer')))

    # for _dir, sub_dirs, files in ln.walk('/root/test'):
    #     print _dir, sub_dirs, files
