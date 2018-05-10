#!/usr/bin/env python
import re
import random, string

def get_index(config_content, res_param):
    """
    Returns the index of line to append resource param.
    :param config_content: File content list
    :param res_param: resource name to search
    :return: Index from list to append new line
    """
    for line in config_content:
        if line.strip():
            if res_param in line:
                continue
            else:
                index = config_content.index(line)
                break
    return index

def create_config(config_path, res_param, **kwargs):
    """
    Open config file in write mode and add the contents
    :return:
    """
    with open(config_path, 'r+') as f:
        file_content = f.readlines()
        index = get_index(file_content, res_param)
        hd_name = ''.join(random.choice(string.lowercase) for x in range(6))
        for host in kwargs.get('hostname', None):
            file_content.insert(index, 'hd={},system={}\n'.format(hd_name, host))
            index += 1
        f.seek(0)
        f.truncate()
        for line in file_content:
            f.write(line)

if __name__ == '__main__':
    create_config('qcsbench', res_param='hd=', hostname=['192.168.102.13'])
