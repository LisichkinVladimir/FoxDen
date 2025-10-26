create table device_types
(
	id      serial primary key,     -- Идентификатор
	name    varchar(100) not null,  -- Название типа устройства
	code    varchar(100) not null,  -- Код типа устройства
	state   boolean not null,       -- Статус (удален не удален)
	unique (name),
	unique (code)
);
comment on table device_types           is 'Типы устройств';
comment on column device_types.id       is 'Идентификатор типа устройства';
comment on column device_types.name     is 'Название типа устройства';
comment on column device_types.code     is 'Код типа устройства';
comment on column device_types.state    is 'Статус типа устройства';