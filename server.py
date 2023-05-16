#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: Yotam Ben Dov 316387950
@author: Nili Alfia 314880873
"""
import sys, os, random, string, socket
import utils

# sizes
TYPE = 4  # file type (file or directory).
DEVICE_NUM = 4  # allows 10k devices per user.
ACTION = 6  # corresponds to reported events from observer.
PATH_LEN = 8  # path's length shouldn't be over 10^8.
FILE_SIZE = 16  # maximum file size at 10^16.
ID_SIZE = 128  # default size of login key.
CHUNK = 4096  # a moderate chunk of data.

# miscellaneous
FORMAT = "UTF-8"  # encoding format used.
LOGIN = "signin"
REGISTER = "signup"
DONE = "done"
UPDONE = "updone"
CHARS = string.ascii_letters + string.digits  # list of possible digits for id.

# file types
FILE = "file"
DIRECTORY = "fdir"

# actions
CREATE = "create"
MOVE = "rename"
DELETE = "delete"
MODIFY = "modify"

users = {}


def main(port_num):
    """
    the main function of the cloud server.

    Parameters
    ----------
    port_num : int
        the desired port to which the server will try to bind.

    Returns
    -------
    None.

    """
    # creates server and starts listening to clients.
    server = socket.create_server(("", int(port_num)))
    server.listen()
    # gets current directory.
    default_dir = os.getcwd()
    # while receiving clients.
    while True:
        # connects to client device.
        user, client = connect(server)
        # prepares for updates.
        os.chdir(user.get_folder())
        # updates files.
        update(client, user)
        # reverts to original server directory and closes client.
        os.chdir(default_dir)
        client.close()


def update(client, user):
    """
    updates server and relevant user devices.

    Parameters
    ----------
    client : socket
        client socket.
    user : User
        user object.

    Returns
    -------
    None.

    """
    # sends updates and then receives updates from client.
    utils.send_updates(client, user.get_device())
    utils.receive_updates(client, user.get_device(), user)


def connect(server):
    """
    connects server to client.

    Parameters
    ----------
    server : socket
        server socket.

    Returns
    -------
    user : User
        user object.
    client : socket
        client socket.

    """
    # accept client
    client = server.accept()[0]
    # check if login or register
    action = client.recv(ACTION).decode()
    # according to given action, registers a new user or logs in and old one.
    if action == REGISTER:
        user = register(client)
    else:
        user = login(client)
    device_num = user.get_dev_num()
    # set given device num as current device.
    user.set_device(device_num)
    # returns User object, appropriate device and connected client.
    return user, client


def login(client):
    """
    logs client in.

    Parameters
    ----------
    client : socket
        client socket.

    Returns
    -------
    user : User
        relevant user to the logged in client.

    """
    # receives key.
    key = client.recv(ID_SIZE).decode()
    # gets user.
    user = users[key]
    # receives device num from client.
    device_num = client.recv(DEVICE_NUM).decode()
    # if doesn't have one, assigns a new one and send it to client.
    if device_num == "None":
        device_num = user.add_device()
        client.send(bytes(device_num, FORMAT))
        # adds all file in folder to be uploaded.
        utils.upload_all(
            user.get_device(device_num), user.get_folder(), user.get_folder()
        )
    # sets as current device.
    user.set_device(device_num)
    return user


def register(client):
    """
    registers a new user to server.

    Parameters
    ----------
    client : socket
        client socket.

    Returns
    -------
    users[key] : User
        new user object.

    """
    # create new key for user, create folder.
    key = "".join(random.choice(CHARS) for c in range(ID_SIZE))
    user_folder = f"user{len(users)}"
    # tries to create a folder, if exists deletes and tries again.
    try:
        os.mkdir(user_folder)
    except:
        utils.delete_dir(user_folder, user_folder)
        os.mkdir(user_folder)
    # insert new User into user dictionary.
    users[key] = utils.User(user_folder)
    # send key and device num to client.
    client.send(bytes(key, FORMAT))
    print(key)
    client.send(bytes(str(users[key].get_device().get_num()), FORMAT))
    return users[key]


if __name__ == "__main__":
    main(int(sys.argv[1]))
