#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: Yotam Ben Dov 316387950
@author: Nili Alfia 314880873
"""

import os
from watchdog.events import FileSystemEventHandler

# to avoid magic numbers etc.

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
FAIL = "fail"

# file types
FILE = "file"
DIRECTORY = "fdir"

# actions
CREATE = "create"
MOVE = "rename"
DELETE = "delete"
MODIFY = "modify"
UPDONE = "updone"


class Handler(FileSystemEventHandler):
    """ """

    def __init__(self, device, path):
        """
        

        Parameters
        ----------
        device : TYPE
            DESCRIPTION.
        path : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        """
        FileSystemEventHandler()
        self.device = device
        self.path = path

    # miscellaneous methods.
    def get_path(self):
        # returns copy of handler's path.
        return self.path

    def get_device(self):
        # returns device.
        return self.device

    # overriding methods.
    def on_created(self, event):
        # file is created event.
        relative_path = os.path.relpath(event.src_path, self.path)
        self.device.create(relative_path)

    def on_modified(self, event):
        # file is modified event.
        if not event.is_directory:
            relative_path = os.path.relpath(event.src_path, self.path)
            self.device.modify(relative_path)

    def on_deleted(self, event):
        # file is deleted event.
        relative_path = os.path.relpath(event.src_path, self.path)
        self.device.delete(relative_path)

    def on_moved(self, event):
        # file is moved event.
        src = os.path.relpath(event.src_path, self.get_path())
        dest = os.path.relpath(event.dest_path, self.get_path())
        self.device.move(src, dest)


class User:
    """
    user class object.
    """

    def __init__(self, folder):
        """
        Parameters
        ----------
        folder : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        """
        self.folder = folder
        self.cur_device = Device("0000")
        self.devices = [self.cur_device]

    # getters.
    def get_folder(self):
        # returns copy of folder path.
        return self.folder

    def get_devices(self):
        # returns copy of device list.
        return self.devices.copy()

    def get_device(self, device_num=None):
        # returns current working device unless otherwise specified.
        return self.devices[int(device_num)] if device_num else self.cur_device

    def get_dev_num(self, device=None):
        # returns user's device number
        if not device:
            return self.cur_device.get_num()
        return self.devices[device].get_num()

    # setters.
    def set_device(self, device_num):
        self.cur_device = self.devices[int(device_num)]

    def add_device(self):
        # creates a new device
        new_device = Device(f"{len(self.devices)}".zfill(DEVICE_NUM))
        self.devices.append(new_device)
        return new_device.get_num()

    def update_devices(self, action, path, dest=None):
        for i in range(len(self.devices)):
            if i != int(self.cur_device.get_num()):
                if dest:
                    self.devices[i].updates.append((path, dest))
                else:
                    self.devices[i].updates.append((action, path))


class Device:
    """
    """

    def __init__(self, num):
        """
        

        Parameters
        ----------
        num : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        """
        self.dev_num = num
        self.updates = []
        self.last_action = {}

    def get_num(self):
        return self.dev_num

    def delete(self, path):
        if path in self.last_action.keys():
            la_f = self.last_action[path]
            if la_f == CREATE:
                self.updates.remove((CREATE, path))
                self.last_action.pop(path)
            elif la_f == MODIFY:
                self.updates.remove((MODIFY, path))
                self.updates.append((DELETE, path))
                self.last_action[path] = DELETE
            elif isinstance(la_f, tuple):
                self.updates.remove(la_f)
                self.delete(la_f[0])
                self.last_action.pop(path)
        else:
            self.updates.append((DELETE, path))
            self.last_action[path] = DELETE

    def modify(self, path):
        if path in self.last_action.keys():
            la_f = self.last_action[path]
            if isinstance(la_f, tuple):
                self.updates.remove(la_f)
                self.updates.append((MODIFY, path))
                self.last_action[path] = MODIFY
                self.delete(la_f[0])
            elif la_f == DELETE:
                self.create(path)
        else:
            self.updates.append((MODIFY, path))
            self.last_action[path] = MODIFY

    def move(self, src, dest):
        if src in self.last_action.keys():
            la_src = self.last_action[src]
            if isinstance(la_src, tuple):
                self.updates.append((src, dest))
                self.last_action[src] = (src, dest)
                self.last_action[dest] = (src, dest)
            else:
                self.delete(src)
                self.modify(dest)
        else:
            self.updates.append((src, dest))
            self.last_action[src] = (src, dest)
            self.last_action[dest] = (src, dest)

    def create(self, path):
        self.updates.append((CREATE, path))
        self.last_action[path] = CREATE

    def clear_la(self):
        self.last_action.clear()

    def ignore(self, lst):
        # removes redundant commands.
        temp = self.updates
        self.updates = [x for x in temp + lst if x not in lst]
        lst = [x for x in lst if x not in temp]


def send_updates(client, device, redundant=[]):
    """
    a function that takes a list of updates from a device and sends them, while
    also removing the last action of files sent.

    Parameters
    ----------
    client : socket
        a socket connected to a server/client.
    device : device object
        a device object hold the device's directory, updates and number.

    Returns
    -------
    None.

    """
    # while there are still updates to send.
    device.ignore(redundant)
    while len(device.updates) > 0:
        # check update and remove it from list.
        command = device.updates.pop(0)
        # if update is create/modify, notify action, upload and update device.
        if command[0] in [CREATE, MODIFY]:
            client.send(bytes(command[0], FORMAT))
            send(client, command[1])
        # else command is delete/move (local), notifies and updates device.
        elif command[0] == DELETE:
            if command[1] in device.last_action:
                device.last_action.pop(command[1])
            to_delete(client, command[1])
        else:
            if command[1] in device.last_action:
                device.last_action.pop(command[1])
            to_move(client, command[0], command[1])
    device.clear_la()
    client.send(bytes(UPDONE, FORMAT))


def to_delete(client, path):
    # send command to delete object at path.
    client.send(bytes(DELETE, FORMAT))
    send_path(client, path)


def to_move(client, src, dest):
    # send command to move object from src to dest
    client.send(bytes(MOVE, FORMAT))
    send_path(client, src)
    send_path(client, dest)


def send_path(client, path):
    # sends path object.
    path_len = f"{len(path):<{PATH_LEN}}"
    client.send(bytes(path_len + path, FORMAT))


def send(client, path):
    """
    navigates between directory sending and file sending.
    Parameters
    ----------
    client : TYPE
        DESCRIPTION.
    path : TYPE
        DESCRIPTION.

    Returns
    -------
    None.

    """
    # sends path and navigates to relevant helper func.
    send_path(client, path)
    if os.path.isfile(path):
        send_file(client, path)
    else:
        client.send(bytes(DIRECTORY, FORMAT))


def send_file(client, path):
    """
    sends a file object's data.

    Parameters
    ----------
    client : socket
        client socket.
    path : stf
        file's path.

    Returns
    -------
    None.

    """
    # sends size and then sends file itself.
    f_size = os.path.getsize(path)
    client.send(bytes(FILE + f"{f_size:<{FILE_SIZE}}", FORMAT))
    file = open(path, "rb")
    client.send(file.read())


def upload_all(device, path, base):
    # for each file in path.
    with os.scandir(path) as fdir:
        for file in fdir:
            # get relative path and add it to updates.
            r_path = os.path.relpath(file.path, base)
            device.create(r_path)
            # if file is a folder, activate recursively.
            if file.is_dir():
                upload_all(device, file.path, base)


def receive_updates(client, device, user=None):
    """
    receives updates from sender.

    Parameters
    ----------
    client : socket
        client socket.
    user : User, optional
        if it's the server, updates devices. The default is None.

    Returns
    -------
    list of duplicate commands to ignore.

    """
    redundant_updates = []
    # while there are still updates to send, gets update action and path.
    while True:
        action = client.recv(ACTION).decode()
        # elif done uploading, breaks out of loop.
        if action == UPDONE:
            break
        path = receive_path(client)
        # if update is create or modify, receives file to given path.
        if action in [CREATE, MODIFY]:
            f_type = client.recv(TYPE).decode()
            if f_type == DIRECTORY:
                receive_dir(path)
            else:
                receive_file(client, path)
        # elif update is to delete, seperate cases for directories and files.
        elif action == DELETE:
            if os.path.isdir(path):
                delete_dir(path, path)
            else:
                os.remove(path)
        # else it's a move command, receives dest and moves file.
        else:
            action = path
            path = receive_path(client)
            if os.path.isdir(action):
                try:
                    move_dir(action, path)
                except OSError:
                    delete_dir(path, path)
                    move_dir(action, path)
            else:
                os.replace(action, path)
        redundant_updates.append((action, path))
        if user:
            user.update_devices(action, path)
    return redundant_updates


def move_dir(src, dest):
    """
    moves src directory with files to dest.
    """
    # tries to create destination folder
    try:
        os.mkdir(dest)
    # regardless, scans subfiles and folders and sends recursively.
    finally:
        with os.scandir(src) as fdir:
            for file in fdir:
                new = os.path.join(dest, file.name)
                # enters recursion if file is dir.
                if file.is_dir:
                    os.mkdir(new)
                    move_dir(file.path, new)
                # else moves file.
                else:
                    os.replace(file.path, new)
    # deletes original directory at the end.
    os.rmdir(src)


def delete_dir(cur_dir, base):
    # removes directories with files recursively.
    with os.scandir(cur_dir) as fdir:
        for file in fdir:
            if file.is_file():
                os.remove(file.path)
            else:
                delete_dir(file.path, base)
    os.rmdir(cur_dir)


def receive_dir(path):
    # tries to create a directory, else nothing.
    try:
        os.mkdir(path)
    finally:
        pass
    return path


def receive_file(client, path):
    # receives a file from client at location path.
    f_size = receive_file_size(client)
    # writes as long as there's still information incoming.
    with open(path, "wb") as file:
        while f_size > 0:
            data = client.recv(f_size)
            file.write(data)
            f_size -= len(data)


def receive_path(client):
    # receives path.
    temp = client.recv(PATH_LEN).decode()
    length = int(temp)
    return client.recv(length).decode()


def receive_file_size(client):
    # receives file's size.
    temp = client.recv(FILE_SIZE).decode()
    return int(temp)
