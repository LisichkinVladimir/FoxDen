create table device_changes
(
	device_id   integer not null,						-- Идентификатор устройства
	moment      timestamp with time zone not null,	    -- Время поступления информации
	foreign key (device_id) references devices(id)
);
comment on table device_changes             is 'Информация об изменения утройств';
comment on column device_changes.device_id  is 'Идентификатор устройства';
comment on column device_changes.moment     is 'Время поступления информации';
create index device_changes_ui on device_changes (device_id, moment);