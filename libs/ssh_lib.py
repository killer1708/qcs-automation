#!/usr/bin/env python
"""
ssh_lib.py: Establishes ssh connection to host
"""

# from python lib
import os
import paramiko
import pexpect
import time

# from external lib
from scp import SCPClient

# from qcs-automation libs
from libs.log.logger import Log

# create log object
log = Log()


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
            child = pexpect.spawn('ssh {}@{}'.format(self.user,
                                  self.ip_address))
            res = child.expect([pexpect.TIMEOUT, ' (yes/no)?'])
            child.sendline('yes')
            # This sleep will help for pexpect to work
            time.sleep(5)
        except Exception as e:
            log.error("Unable to connect remote server")

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
            log.info("Executing command: {} on {}".format(cmd,
                      self.ip_address))
            stdin, stdout, stderr = self.conn.exec_command(cmd)
            try:
                stdoutbuffer = stdout.read()
            except Exception as e:
                stdout = str(e)

            try:
                stderrbuffer = stderr.read()
            except Exception as e:
                stderr = str(e)

            try:
                if not isinstance(stdout, str):
                    status = stdout.channel.recv_exit_status()
                else:
                    status = None
            except Exception as e:
                status = str(e)

            if not isinstance(stdout, str):
                stdout = stdoutbuffer.decode('utf8')
            if not isinstance(stderr, str):
                stderr = stderrbuffer.decode('utf8')
            log.info("Command status: {}".format(status))
            log.debug(stdout.splitlines())
            log.debug(stderr.splitlines())
            return (status, stdout.splitlines(), stderr.splitlines())
        except Exception as e:
            log.error("Unable to connect remote server {}"\
                      .format(self.ip_address))
            log.error(e)
            if 'SSH session not active' in str(e):
                log.info("Restablising connection on {}"\
                         .format(self.ip_address))
                # re-establish connection and execute the command
                self._init_connection()
                self.execute_command(cmd)
            return None, None, None

    def scp_get(self, *, remotepath, localpath, recursive=False):
        """
        Scp files/dir from SSH server
        """
        scp = SCPClient(self.conn.get_transport())
        try:
            scp.get(remotepath, localpath, recursive, preserve_times=True)
        except Exception as e:
            log.info("Hit exception while scp_get from {} to {} on {}".format(
                     remotepath, localpath, self.ip_address))
            log.info(e)
            raise
        return True

    def scp_put(self, *, localpath, remotepath, recursive=False):
        """
        Scp files/dir to SSH server
        """
        scp = SCPClient(self.conn.get_transport())
        try:
            scp.put(localpath, remotepath, recursive)
        except Exception as e:
            log.info("Hit exception while scp_put from {} to {} on {}".format(
                     localpath, remotepath, self.ip_address))
            log.info(e)
            raise
        return True

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
                log.info(sftp.stat(remotepath))
                log.info("File exists {}".format(remotepath))
            except IOError:
                log.info("Copying file {} to {}".format(localpath, remotepath))
                sftp.put(localpath, os.path.abspath(remotepath))
            sftp.close()
        except paramiko.SSHException as e:
            log.error("Connection Error: {}".format(e))


if __name__ == '__main__':
    print("Module loaded successfully.")

