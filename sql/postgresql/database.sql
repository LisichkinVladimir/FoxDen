-- drop database if exists foxden;

create database foxden
    with
    owner = postgres
    encoding = 'utf8'
    lc_collate = 'russian_russia.1251'
    lc_ctype = 'russian_russia.1251'
    locale_provider = 'libc'
    tablespace = pg_default
    connection limit = -1
    is_template = false;