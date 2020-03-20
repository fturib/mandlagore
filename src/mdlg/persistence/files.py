import tarfile
from zipfile import ZipFile
import os
from shutil import rmtree


def untar(src_file, dest_dir, filter_on_name=None):
    # filter is a function that accept a TarInfo as parameter and return True if corresponding file should be extracted

    tf = tarfile.open(src_file, 'r')
    try:
        members = None
        if filter_on_name is not None:
            members = filter(lambda x: filter(x.name), tf.getmembers())
        tf.extractall(dest_dir, members)
    finally:
        tf.close()


def unzip(src_file, dest_dir, filter_on_name=None):
    with ZipFile(src_file) as zip:
        members = None
        if filter_on_name is not None:
            members = filter(filter_on_name, zip.namelist())
        zip.extractall(dest_dir, members)


def extract(src_file: str, dest_dir: str, filter_on_name=None):
    rmtree(dest_dir)
    os.makedirs(dest_dir, 0o777, exist_ok=False)
    try:
        untar(src_file, dest_dir, filter_on_name)
    except Exception as e:
        unzip(src_file, dest_dir, filter_on_name)
