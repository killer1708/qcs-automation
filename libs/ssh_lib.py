import os
import paramiko
import pexpect
import time

class SshConn(object):
    def __init__(self, ip, user, password):
        self.ip_address = ip
        self.user = user
        self.password = password
        self.conn = None

    def _init_connection(self):
        """
        Initiate ssh connection
        :return: None
        """
        try:
            self.conn = paramiko.SSHClient()
            self.conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.conn.connect(self.ip_address, username=self.user,
                              password=self.password)
            child = pexpect.spawn('ssh {}@{}'.format(self.user, self.ip_address))
            res = child.expect([pexpect.TIMEOUT, ' (yes/no)?'])
            child.sendline('yes')
            # This sleep will help for pexpect to work
            time.sleep(5)
        except Exception as e:
            print("Unable to connect remote server")

    def execute_command(self, cmd):
        """
        Execute command
        :param cmd: Command to be executed
        :return: return tuple of (stdout, stderr)
        """
        try:
            if not isinstance(cmd, str):
                cmd = ' '.join(arg for arg in cmd)
            if not self.conn:
                self._init_connection()
            ssh_stdin, ssh_stdout, ssh_stderr = self.conn.exec_command(cmd)
            return ssh_stdin, ssh_stdout.read().splitlines(), ssh_stderr.read().splitlines()
        except Exception as e:
            print("Unable to connect remote server")
            return None, None, None

    def copy_command(self, localpath, remotepath):
        """
        copy file to remote server
        :param localpath: local path of the file
        :param remotepath: path where file should get copied
        """
        try:
            if not self.conn:
                self._init_connection()
            sftp = self.conn.open_sftp()
            try:
                print(sftp.stat(remotepath))
                print('file exists')
            except IOError:
                print('copying file')
                sftp.put(localpath, os.path.abspath(remotepath))
            sftp.close()
        except paramiko.SSHException:
            print("Connection Error")

if __name__ == '__main__':
    '''
    conn = SshConn('192.168.105.20', 'root', 'master@123')
    _, stdout, stderr = conn.execute_command("lsblk -d -n -oNAME | awk {'print $1'}")
    print(stdout, stderr)
    for i in stdout:
             if b"sda" in i:
                 pass 
             elif b"sr0" in i:
                 pass
             else:
                 disk = i.decode(encoding='UTF-8',errors='strict')
                 print("disk=", disk)
    '''
    conn = SshConn('192.168.102.85', 'administrator', 'master@123')
    #_, stdout, stderr = conn.execute_command('echo y | ssh-keygen -t rsa -f /root/.ssh/id_rsa -q -P ""'))
    _, stdout, stderr = conn.execute_command("cmd \/c IOmeter.exe /c test_iometer.icf /r result.csv")
    #_, stdout, stderr = conn.execute_command('cmd \/c echo y | pscp.exe -pw master@123 \
    #                    root@192.168.105.122:/root/automation/qcs-automation/libs/test.py test.py ')
    print(stdout, stderr)
    '''
    try:
        _, stdout, stderr = conn.execute_command("firewall-cmd --state")
        print(stdout, stderr)
        if stderr and b"not" in stderr[0]:
            print("Firewall not running ...")
        else:
            command = "systemctl stop firewalld"
            _, stdout, stderr = conn.execute_command(command)
            print("Warning : Firewall is stopped, please start the firewall\
                   once execution is complete...")
    except Exception as e:
        print("Something goes wrong",str(e))
    '''
    
