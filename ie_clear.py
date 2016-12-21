import os

CLEAR_COMMAND = 'RunDll32.exe InetCpl.cpl,ClearMyTracksByProcess %s'

TEMPORARY_IDX = 8
COOKIES_IDX = 2
HISTORY_IDX = 1
FORMDATA_IDX = 16
PASSWORD_IDX = 32
ALL_IDX = 255
DELETE_ALL_IDX = 4351


def _clear(idx):
    os.popen(CLEAR_COMMAND % idx)


def clear_temporary_files():
    _clear(TEMPORARY_IDX)


def clear_cookies():
    _clear(COOKIES_IDX)


def clear_history():
    _clear(HISTORY_IDX)


def clear_form_data():
    _clear(FORMDATA_IDX)


def clear_password():
    _clear(PASSWORD_IDX)


def clear_all():
    _clear(ALL_IDX)


def delete_all():
    _clear(DELETE_ALL_IDX)
