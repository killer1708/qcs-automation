import time

from nodes.node import Linux

NFS_SERVER = '192.168.102.13'
VDBENCH_MOUNT_LOCATION = '/var/vdbench_share'


def vdbench_deploy(node, repository=None):
    vdbench_dir = '/opt/vdbench'
    exe = 'vdbench'
    vdbench_exe = '{}{}{}'.format(vdbench_dir, node.path_seperator(), exe)
    mnt_dir = '/mnt/dir'
    if not repository:
        repository = '{}:{}'.format(NFS_SERVER, VDBENCH_MOUNT_LOCATION)
    mount_cmd = ['mount', repository, mnt_dir]
    res, error = node.ssh_conn.execute_command(['java', '-version'])
    # Todo: java -version print result in stderr instead of stdout
    if error:
        print "deploying Java..............."
        node.deploy('java')
    if node.is_path_exists(vdbench_exe):
        print "vdbench present already ........"
        return vdbench_exe
    for _dir in (vdbench_dir, mnt_dir):
        node.makedir(_dir)
    print "fetching vdbench and deploying ......."
    node.deploy('nfs-utils')
    _, error = node.ssh_conn.execute_command(mount_cmd)
    for base, _dir, files in node.walk(mnt_dir):
        if exe in files:
            base_dir = '{}/*'.format(base)
            node.ssh_conn.execute_command(['cp', '-rp', base_dir, vdbench_dir])
            time.sleep(20)
            _, error = node.ssh_conn.execute_command(['umount', mnt_dir])
            print error
            return vdbench_exe


def main():
    ln = Linux('192.168.105.30', 'root', 'master@123')
    print vdbench_deploy(ln)

main()
