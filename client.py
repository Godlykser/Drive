#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: Yotam Ben Dov 316387950
@author: Nili Alfia 314880873
"""
import sys
import os
import socket
import time  # allowed libraries
import utils  # in common functions
from watchdog.observers import Observer

# sizes
TYPE = 4  # file type (file or directory).
DEVICE_NUM = 4  # allows 10k devices per user.
ACTION = 6  # corresponds to reported events from observer.
PATH_LEN = 8  # path's length shouldn't be over 10^8.
NAME_SIZE = 10  # name shouldn't be longer than 10^10 either.
FILE_SIZE = 16  # maximum file size at 10^16.
ID_SIZE = 128  # default size of login key.
CHUNK = 4096  # a moderate chunk of data.

# miscellaneous
FORMAT = "UTF-8"  # encoding format used.
LOGIN = "signin"
REGISTER = "signup"
DONE = "done"
UPDONE = "updone"

# file types
FILE = "file"
DIRECTORY = "fdir"

# actions
CREATE = "create"
MOVE = "rename"
DELETE = "delete"
MODIFY = "modify"


def main(s_ip, s_port, dir_path, connection_time, identifier=None):
    """
    client's main function

    Parameters
    ----------
    s_ip : string
        server's IP address
    s_port : int
        server's port number
    dir_path : string
        the chosen folder to upload from (new user) or download to (login)
    connection_time : int
        how often to try and connect with the server to update changes or get
        updates on changes from other PCs
    identifier : string, optional
        the identifying code for a returning user. The default is None.

    Returns
    -------
    None.

    """
    # tupple of server details.
    server = (s_ip, s_port)
    # sets given path as current work directory.
    if identifier:
        os.mkdir(dir_path)
    os.chdir(dir_path)
    # connects to server and gets client, user's key and current device.
    client, key, device = connect(server, identifier, dir_path)
    # updates files.
    utils.receive_updates(client, device)
    utils.send_updates(client, device)
    # shutdown client socket.
    client.shutdown(socket.SHUT_RDWR)
    client.close()
    # start watching directory.
    handler = utils.Handler(device, dir_path)
    observer = Observer()
    observer.schedule(handler, dir_path, recursive=True)
    observer.start()
    # duplicate command list.
    redundant = []
    while True:
        # wait to connect to server.
        time.sleep(int(connection_time))
        client = connect(server, key, dir_path, device)[0]
        # receives updates and keep the redundants.
        redundant += utils.receive_updates(client, device)
        # sends commands while removing redundant commands.
        utils.send_updates(client, device, redundant)
        client.shutdown(socket.SHUT_RDWR)
        client.close()


def connect(server, key, path, device=None):
    """
    connects to server.

    Parameters
    ----------
    server : socket
        server socket.
    key : str
        user id.
    path : str
        path to given directory.
    device : Device, optional
        current device's Device object. The default is None.

    Returns
    -------
    client : ocket
        server socket.
    key : str
        user id.
    device : Device, optional
        current device's Device object.

    """
    # creates client socket
    client = socket.create_connection(server)
    # if no key, it's new client - returns new key and 0000 as device num.
    if not key:
        key, device = register(client, path)
    # if no prior device - new device.
    elif not device:
        device = login(client, key)
    # else it's an old device.
    else:
        login(client, key, device.get_num())
    # return connection details.
    return client, key, device


def register(client, path):
    """
    registers a new user.

    Parameters
    ----------
    client : socket
        client's socket.
    path : str.
        folder to upload..

    Returns
    -------
    key : str
        id for registered user.
    device : Device
        device object for current console.

    """
    # notifies server about new user.
    client.send(bytes(REGISTER, FORMAT))
    # receives user's key.
    key = client.recv(ID_SIZE).decode()
    # receives new device's num and creates a new device object.
    device_num = client.recv(DEVICE_NUM).decode()
    device = utils.Device(device_num)
    # sets all items in given path to be uploaded to server.
    utils.upload_all(device, path, path)
    return key, device


def login(client, key, device_num=None):
    """
    logs into server.

    Parameters
    ----------
    client : socket.
        client socket.
    key : str
        identifier.
    device_num : str, optional
        current device's id. The default is None.

    Returns
    -------
    TYPE
        DESCRIPTION.

    """
    # sends details.
    client.send(bytes(str(LOGIN), FORMAT))
    client.send(bytes(str(key), FORMAT))
    client.send(bytes(str(device_num), FORMAT))
    # if no current device, receives new device and returns created device.
    if device_num is None:
        device_num = client.recv(DEVICE_NUM).decode()
    return utils.Device(device_num)


if __name__ == "__main__":
    if len(sys.argv) == 5:
        main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        main(sys.argv[1], int(sys.argv[2]),
             sys.argv[3], int(sys.argv[4]), sys.argv[5])
