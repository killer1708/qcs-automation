import paramiko
import pexpect

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
        self.conn = paramiko.SSHClient()
        self.conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.conn.connect(self.ip_address, username=self.user,
                          password=self.password)
        child = pexpect.spawn('ssh {}@{}'.format(self.user, self.ip_address))
        child.expect(['(yes/no)?'])
        child.sendline('yes')

    def execute_command(self, cmd):
        """
        Execute command
        :param cmd: Command to be executed
        :return: return tuple of (stdout, stderr)
        """
        if not isinstance(cmd, str):
            cmd = ' '.join(arg for arg in cmd)
        if not self.conn:
            self._init_connection()
        ssh_stdin, ssh_stdout, ssh_stderr = self.conn.exec_command(cmd)
        return ssh_stdin, ssh_stdout.read().splitlines(), ssh_stderr.read().splitlines()
