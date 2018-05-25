import time

from nodes.node import Linux
from libs.ovirt_engine import create_vm_from_template, get_vm_ip
from libs.vdb_config import create_config

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
    _, res, error = node.ssh_conn.execute_command(['java', '-version'])
    if error:
        if not any("openjdk version" in line for line in error):
            print "deploying Java..............."
            node.deploy('java')
    if node.is_path_exists(vdbench_exe):
        print "vdbench present already ........"
        return vdbench_exe
    for _dir in (vdbench_dir, mnt_dir):
        node.makedir(_dir)
    print "fetching vdbench and deploying ......."
    node.deploy('nfs-utils')
    _, _, error = node.ssh_conn.execute_command(mount_cmd)
    for base, _dir, files in node.walk(mnt_dir):
        if exe in files:
            base_dir = '{}/*'.format(base)
            node.ssh_conn.execute_command(['cp', '-rp', base_dir, vdbench_dir])
            time.sleep(20)
            _, _, error = node.ssh_conn.execute_command(['umount', mnt_dir])
            print error
            return vdbench_exe


def main():
    vms = create_vm_from_template('newcl', 'automation-template', 'data1', 'Demo_VM')
    # vms = get_vm_ip()
    print vms
    ln = Linux(vms[0], 'root', 'master@123')
    vdbench_exe = vdbench_deploy(ln)
    master_node = Linux('192.168.102.13', 'root', 'master#123')
    vdbench_exe = vdbench_deploy(master_node)
    vdbench_conf = create_config('/root/qcs_automation/libs/qcsbench', res_param='hd=', hostname=[vms[0]])
    print vdbench_conf
    print vdbench_exe
    vdbench_cmd = '{} -f {}'.format(vdbench_exe, vdbench_conf)
    print vdbench_cmd
    stdin, res, error = master_node.ssh_conn.execute_command(vdbench_cmd)

main()
