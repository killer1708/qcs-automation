#!/usr/bin/env python
"""
run.py: Execute vdbench test as per config.py
"""

# from python lib
import os
import sys
import time
import tempfile
import subprocess
import threading

# from qcs-automation libs
from nodes.node import Linux, Windows
from libs.ovirt_engine import OvirtEngine
from libs.log.logger import Log
from tools.qcsbench.vdbench import config

# create log object
log = None
if os.environ.get('USE_ROBOT_LOGGER', None) == "True":
    from lib.log.logger import Log
    log = Log()
else:
    log = Log()

VDBENCH_MOUNT_LOCATION = '/var/vdbench_share'
VDBENCH_EXE_LOC = "/opt/vdbench"
VDBENCH_LOGS = "/opt/vdbench/output_dir"
WIN_VDBENCH_EXE_LOC = "vdbench"

def vdbench_deploy(host):
    """
    Deploy vdbench on a host
    :param host - host where vdbench need to be deployed
    :return None
    """
    if host.host_type == 'linux':
        vdbench_exe = "{}/vdbench".format(VDBENCH_EXE_LOC)
        # check vdbench
        log.info("Check if vdbench already present")
        if host.is_path_exists(vdbench_exe):
            log.info("vdbench exe already present on host {}".format(host))
            return
        # check java & deploy if not available
        log.info("Verify if java alredy presnt")
        status, output, error = host.conn.execute_command(['java', '-version'])
        if status:
            log.info(output)
            log.error(error)
        else:
            log.info("java already present on host {}".format(host))
        if not any("openjdk version" in line for line in error):
            log.info("Deploying Java on host {}".format(host))
            host.deploy('java')
        # copy vdbench source files to the host
        log.info("Copying vdbench source files to host {}".format(host))
        host.conn.scp_put(localpath=VDBENCH_EXE_LOC,
                              remotepath=os.path.dirname(VDBENCH_EXE_LOC),
                              recursive=True)
        log.info("Successfully copied vdbench source files to host {}".format(host))
    elif host.host_type == 'windows':
        # vdbench_exe = "{}\\vdbench.bat".format(WIN_VDBENCH_EXE_LOC)
        pass

def key_is_present(host):
    """
    Verify the key is present on the host
    """
    if(config.HOST_TYPE == 'linux'):
        status, stdout, stderr =  host.conn.execute_command('ls /root/.ssh')
        if status:
            return False
        if 'id_rsa.pub' in stdout[0]:
            return True
        return False
    else:
        status, stdout, stderr =  host.conn.execute_command('cmd /c dir "C:\\Program Files (x86)\\freeSSHd"')
        if status:
            return False
        for value in stdout:
            if 'RSAKey.cfg' in value:
                return True
        return False

def push_key_to_slave(master_node, slave_vms):
    """
    Copy public key of master to slave VMs
    """
    if(config.HOST_TYPE == 'linux'):
        command = 'cat /root/.ssh/id_rsa.pub'
        _, stdout, stderr = master_node.conn.execute_command(command)
        key_data = stdout[0]
        for slave_node in slave_vms:
            # Create directory if it doesn't exists
            slave_node.makedir('/root/.ssh')
            command = 'echo {} >> /root/.ssh/authorized_keys'.format(key_data)
            status, stdout, stderr = slave_node.conn.execute_command(command)
            if status:
                log.info(stdout)
                log.error(stderr)
        # disable strict host ksy checking
        data = 'Host *\nStrictHostKeyChecking no\nUserKnownHostsFile=/dev/null'
        command = "echo -e '{}' > /root/.ssh/config".format(data)
        status, stdout, stderr = master_node.conn.execute_command(command)
    else:
        command = 'cmd /c type "C:\\Program Files (x86)\\freeSSHd\\RSAKey.cfg"'
        _, stdout, stderr = master_node.conn.execute_command(command)
        key_data = ""
        for line in stdout:
            champ=key_data+line.strip('\n')
        for slave_node in slave_vms:
            # Create directory if it doesn't exists
            slave_node.makedir('C:\\.ssh')
            command = 'cmd /c echo {} >> C:\\.ssh\\authorized_keys'.format(key_data)
            status, stdout, stderr = slave_node.conn.execute_command(command)
            if status:
                log.info(stdout)
                log.error(stderr)

def generate_key(master_node):
    """
    Generate ssh key
    """
    # Genarate private key
    master_node.conn.execute_command(
                        'echo y | ssh-keygen -t rsa -f /root/.ssh/id_rsa -q -P ""')

def check_firewalld(master_node):
    """
    Check firewall status,if its running then stop
    """
    try:
        _, stdout, stderr = master_node.conn.execute_command("firewall-cmd --state")
        if stderr and 'not' in stderr[0]:
            log.info("Firewall is not running")
        else:
            command = 'systemctl stop firewalld'
            _, stdout, stderr = master_node.conn.execute_command(command)
            log.warn("Firewall is stopped, please start the firewall +\
                      once execution completes")
    except Exception as e:
        print("Something goes wrong")

def configure_master_host(master_node, slave_nodes, host_type='linux'):
    """
    This will copy master ssh key to all the slave VM's for
    password less authentication.
    """
    if (host_type=='linux'):
        check_firewalld(master_node)
    if not key_is_present(master_node):
        generate_key(master_node)
    push_key_to_slave(master_node, slave_nodes)

def generate_paramfile(load_type, hosts, conf):
    """
    Generate parameter file for given load type
    :param load_type - file_io|block_io
    :param hosts - list of host objects
    :param conf - Workload info dictionary
    """
    block_io = False
    file_io = False
    # Check for file/block IO
    if load_type.lower() == 'block_io':
        block_io = True
    elif load_type.lower() == 'file_io':
        file_io = True

    if block_io:
        newconf = list() 
        i = 1
        sd_params = []
        # add hd params
        if(config.HOST_TYPE == 'linux'):
            hd_params = "hd={},shell=ssh,system={},user=root,vdbench={}"\
                .format(str(hosts),
                        str(hosts),
                        VDBENCH_EXE_LOC)
        else:
            hd_params = "hd={},shell=ssh,system={},user=root,vdbench=C:\\{}"\
                .format(str(hosts),
                        str(hosts),
                        WIN_VDBENCH_EXE_LOC) 
        newconf.append(hd_params)

        # terminate if no disk found for a host
        if not hosts.disks:
            log.info("Disks are: {}".format(hosts.disks))
            raise Exception("No disks found for host {}".format(
                str(hosts)))
        for disk in hosts.disks:
            if conf.get('sd_params'):
                temp = []
                for key, value in conf['sd_params'].items():
                    temp.append("{}={}".format(key, value))
                params = "sd=sd_{},host={},lun={},{}".format(
                          i, str(hosts), disk, ','.join(temp))
            else:
                params = "sd=sd_{},host={},lun={}".format(
                          i, str(hosts), disk)
            sd_params.append(params)
            # increment i
            i += 1
        # disk for loop ends here

        wd_params = []
        for sd_line in sd_params:
            sd = sd_line.split(',')[0].split('=')[1]
            if conf.get('wd_params'):
                temp = []
                for key, value in conf['wd_params'].items():
                    temp.append("{}={}".format(key, value))
                params = "wd=wd_{},sd={},{}".format(sd, sd, ','.join(temp))
            else:
                params = "wd=wd_{},sd={}".format(sd, sd)
            wd_params.append(params)

        if conf.get('rd_params'):
            temp = []
            for key, value in conf['rd_params'].items():
                temp.append("{}={}".format(key, value))
            params = "rd=rd1,wd=*,{}".format(','.join(temp))
        else:
            params = "rd=rd1,wd=*"
        rd_params = [params]

        # add all params
        all_params = sd_params + wd_params + rd_params
        newconf.extend(all_params)

    # block io config generation ends here

    # File IO code block
    if file_io:
        newconf = list()
        if(config.HOST_TYPE=="linux"):
            newconf.append("hd=default,shell=ssh,user=root,vdbench={}"\
                           .format(VDBENCH_EXE_LOC)) 
        else:
            newconf.append("hd=default,shell=ssh,user=admin,vdbench=C:\\{}"\
                           .format(WIN_VDBENCH_EXE_LOC))
        i = 1
        hosts.fsd_params = []
        # add hd params
        hd_params = "hd={},system={}".format(str(hosts), str(hosts))
        newconf.append(hd_params)

        # terminate if no destination location found for host
        if not hosts.mount_locations:
            log.info("Mount locations are {}".format(hosts.mount_locations))
            raise Exception("No filestsem location found for host {}"\
                            .format(str(hosts)))
        log.info("Mount locations are {}".format(hosts.mount_locations))
        for fs in hosts.mount_locations:
            if(config.HOST_TYPE=="linux"):
                if conf.get('fsd_params'):
                    temp = []
                    for key, value in conf['fsd_params'].items():
                        temp.append("{}={}".format(key, value))
                    params = "fsd=fsd_{},anchor={},{}".format(
                              i, fs, ','.join(temp))
                else:
                    params = "fsd=fsd_{},anchor={}".format(i, fs)
            else:
                if conf.get('fsd_params'):
                    temp = []
                    for key, value in conf['fsd_params'].items():
                        temp.append("{}={}".format(key, value))
                    params = "fsd=fsd_{},anchor={},{}".format(
                              i, fs[0], ','.join(temp))
                else:
                    params = "fsd=fsd_{},anchor={}".format(i, fs[0])   
            hosts.fsd_params.append(params)
            # increment i
            i += 1
        # filesystem_locations for loop ends here

        fwd_params = []
        for fsd_line in hosts.fsd_params:
            fsd = fsd_line.split(',')[0].split('=')[1]
            if conf.get('fwd_params'):
                temp = []
                for key, value in conf['fwd_params'].items():
                    temp.append("{}={}".format(key, value))
                params = "fwd=fwd_{},fsd={},host={},{}"\
                         .format(fsd, fsd, str(hosts), ','.join(temp))
            else:
                params = "fwd=fwd_{},fsd={},host={}"\
                         .format(fsd, fsd, str(hosts))
            fwd_params.append(params)
        # inner for loop ends here
        # outer for loop ends here

        if conf.get('rd_params'):
            temp = []
            for key, value in conf['rd_params'].items():
                temp.append("{}={}".format(key, value))
            params = "rd=rd1,fwd=*,{}".format(','.join(temp))
        else:
            params = "rd=rd1,fwd=*"
        rd_params = [params]

        # add all params
        fsd_params = list()
        fsd_params.extend(hosts.fsd_params)
        all_params = fsd_params + fwd_params + rd_params
        newconf.extend(all_params)

    #file io config generation ends here

    temp_paramfile = tempfile.NamedTemporaryFile(delete=False).name
    with open(temp_paramfile, 'w') as fh:
        for line in newconf:
            fh.write(line+"\n")
    return temp_paramfile

def create_window_file_io_file(master_host):
    for value in range(1,(config.DISK_COUNT+1)):
        filename ="/tmp/window_file_io_"+str(value)+".txt" 
        content = open(filename,'w')
        content.write('select disk '+str(value)+'\nattribute disk clear readonly noerr\n\
                       online disk noerr\nlist partition\nconvert gpt noerr\n\
                       create partition primary\nlist partition\nselect partition 2\n\
                       detail partition\nformat quick FS=ntfs label="mount_point" \n\
                       assign mount=C:\mountpoint\ndetail partition')
        content.close()
        master_host.conn.scp_put(localpath=filename,remotepath=WIN_VDBENCH_EXE_LOC)

def get_current_host_ip():
    ip = subprocess.check_output('hostname -I | cut -d\" \" -f 1', shell=True)
    ip = ip.decode(encoding='UTF-8',errors='strict')
    return ip.rstrip('\n')

def execute_vdbench(thread_id, ovirt):
    log_dir = config.LOG_DIR
    log.info("Step 1. Creating {} VM(s)".format(config.SLAVE_VM_COUNT))
    vm_name = config.VM_NAME + str(thread_id)
    vm = ovirt.create_vm_from_template(vm_name,
                                       config.CLUSTER_NAME,
                                       config.TEMPLATE_NAME,
                                       config.TEMPLATE_DS)
    attempt_for_ip = 1
    while(attempt_for_ip < 11):
        ip = ovirt.get_vm_ip(vm.name)
        if ip:
            log.info("IP found for host {}".format(vm.name))
            break
        attempt_for_ip += 1
        if(attempt_for_ip == 11):
            log.critical("No IP found for host {}".format(vm.name))
            sys.exit(1)
        time.sleep(30)
    log.info("VM IP is: {}".format(ip))
    log.info("Creating host objects")
    if config.HOST_TYPE.lower() == 'linux':
        host = Linux(str(ip), config.SLAVE_UNAME, config.SLAVE_PASSWORD)
    elif config.HOST_TYPE.lower() == 'windows':
        host = Windows(str(ip), config.SLAVE_UNAME, config.SLAVE_PASSWORD)
    else:
        log.error("Unknown host type - {}".format(config.HOST_TYPE))
    log.info("Step 2. Add disk to VM(s)")
    for i in range(len(config.INTERFACES)):
        ovirt.add_disk(vm.name,
            "disk_" + str(i),config.INTERFACES[i],
            config.DISK_SIZE_GB,
            config.TEMPLATE_DS,
            config.STORAGE_TYPE, config.POOL_NAME)
        while((ovirt.get_vm_ip(vm.name) == None) or (ovirt.get_vm_ip(vm.name) == "")):
            continue
    log.info("Deploy vdbench on all the hosts")
    #time.sleep(120)
    vdbench_deploy(host)
    host.change_hostname()
    host.refresh_disk_list()
    if config.LOAD_TYPE == 'file_io':
        if(config.HOST_TYPE == 'windows'):
            create_window_file_io_file(host)
            host.create_file_system_on_disks(WIN_VDBENCH_EXE_LOC)
        if(config.HOST_TYPE == 'linux'):
            host.create_file_system_on_disks()
        log.info("Filesystem locations available are - {}"\
                  .format(host.filesystem_locations))
        if(config.HOST_TYPE == 'linux'):
            for i, location in enumerate(host.filesystem_locations):
                mount_point = "/mnt/loc{}".format(i)
                host.makedir(mount_point)
                # mount formatted device on host system
                cmd = "mount {} {}".format(location, mount_point)
                status, stdout, _ = host.conn.execute_command(cmd)
                if status:
                    log.info(stdout)
                    log.error("Unable to mount {} on {}"\
                               .format(location, mount_point))
                # append to mountpoints
                host.mount_locations.append(mount_point)

            log.info("Filesystem mount locations are {}"\
                      .format(host.mount_locations))
        else:
            # append to mountpoints
            host.mount_locations.append(host.filesystem_locations)
            log.info("Filesystem mount locations are {}"\
                      .format(host.mount_locations))
    log.info("Disks are: {}".format(host.disk_list))
    log.info("Configure  host and copy ssh keys to all slaves")
    #configure_master_host(host, host_list ,config.HOST_TYPE)
    # create vdbench temp paramfile based upon load type
    log.info("Step 3. Create vdbench temp paramfile based upon load type")
    temp_paramfile = generate_paramfile(config.LOAD_TYPE, host,
                                    config.WORKLOAD_INFO)
    log.info(temp_paramfile)
    # copy parameter file to host
    if host.host_type == 'linux':
        host.conn.scp_put(localpath=temp_paramfile,
                                     remotepath=VDBENCH_EXE_LOC)
        paramfile = "{}/{}".format(VDBENCH_EXE_LOC,
                                   os.path.basename(temp_paramfile))
        vdbench_exe = VDBENCH_EXE_LOC + "/vdbench"
        logdir = "{}/output".format(VDBENCH_EXE_LOC)
    else:
        host.conn.scp_put(localpath=temp_paramfile,
                                     remotepath=WIN_VDBENCH_EXE_LOC)
        paramfile = "{}\\{}".format(WIN_VDBENCH_EXE_LOC,
                                    os.path.basename(temp_paramfile))
        vdbench_exe = WIN_VDBENCH_EXE_LOC + "\\vdbench.bat"
        logdir = "{}\\output".format(WIN_VDBENCH_EXE_LOC)
    # remove templfile created
    os.unlink(temp_paramfile)
    # prepare vdbench command
    if(config.HOST_TYPE == 'linux'):
        cmd = '{} -f {} -o {}'.format(vdbench_exe, paramfile, logdir)
    else:
        cmd = 'cmd /c C:\\{} -f C:\\{} -o C:\\{}'.format(vdbench_exe, paramfile, logdir)
    if config.DATA_VALIDATION:
        cmd = "{} -v".format(cmd)
    log.info("Step 4. Start the vdbench workload")
    status, stdout, stderr = host.conn.execute_command(cmd)
    if status:
        log.info(stdout)
        log.error(stderr)
    else:
        log.info("VDBench completed successfully.")
    # Collect logs
    log_dir = os.path.join(log_dir, ip)
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    if(config.HOST_TYPE == 'linux'):
        host.conn.scp_get(remotepath=logdir,
                                     localpath=log_dir, recursive=True)
    if(config.HOST_TYPE == 'windows'):
        cmd = 'cmd /c echo y | pscp -r -pw '+str(config.PASSWORD)+' C:\\vdbench\\output '\
            +str(config.USERNAME)+'@'+get_current_host_ip()+':'+os.popen('pwd').read()[:-1]+'/output/'+str(host)
        status, stdout, stderr = host.conn.execute_command(cmd)
    log.info("Collected vdbench logs into {}".format(log_dir))

    # Cleanup paramfile from host
    
    log.info("Cleaning up paramfile on master host")
    if(config.HOST_TYPE == 'linux'):
        cmd = "rm -f {}".format(paramfile)
        _, _, _ = host.conn.execute_command(cmd)
    else:
        cmd = "cmd /c del C:\\{}".format(paramfile)
        _, _, _ = host.conn.execute_command(cmd)
    
    # ovirt.stop_vm(vm.name)

def main():
    """
    Standalone vdbench execution steps:
    precondition: update config.py as per need
    1. create vms
    2. add disks
    3. choose file/block IO
    4. start vdbench load in foreground
    """
    log_dir = config.LOG_DIR 
    if not os.path.isdir(log_dir):
        os.makedirs(log_dir)
    logfile = os.path.join(log_dir, "vdbench_stdout.log")
    log.initialise(logfile, config.LOG_LEVEL)
    log.info("Logs will be collected in '{}' directory".format(log_dir))
    log.info("logfile: {}".format(logfile))

    ovirt = OvirtEngine(config.OVIRT_ENGINE_IP, config.OVIRT_ENGINE_UNAME,
                        config.OVIRT_ENGINE_PASS)
    i = 0
    vm = True
    while(vm):
        vm = ovirt.search_vm(config.VM_NAME + str(i))
        if vm:
            # stop the vm
            ovirt.stop_vm(config.VM_NAME + str(i))
            # remove vm
            ovirt.remove_vm(config.VM_NAME + str(i))
            i+=1
        else:
            break    

    jobs = []
    for thread_id in range(config.SLAVE_VM_COUNT):
        thread = threading.Thread(target=execute_vdbench, args=(thread_id,ovirt,))
        jobs.append(thread)

    log.info(jobs)

    for j in jobs:
        j.start()
        log.info("Thread {}".format(j))

    for j in jobs:
        j.join()

    log.info("List processing complete.")
    
    ovirt.close_connection()


if __name__ == '__main__':
    main()
