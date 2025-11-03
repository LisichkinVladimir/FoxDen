create table devices
(
	id              serial primary key,     -- Идентификатор
	type_id         integer not null,       -- Вид устройства
	mac_address     varchar(100) not null,  -- MAC адрес устройства
	pin             integer not null,       -- Пин устройства
	serial_number   varchar(100) not null,  -- Серийный номер устройства
	scale_unit_id   integer not null,       -- Единица измерения шкалы
	step_increment  integer not null,       -- Шаг увеличения
	indicator       numeric(8, 3),          -- Текущее значение счетчика
	user_id         integer not null,       -- Пользователь счетчика
	state           bool not null,          -- Статус (удален не удален)
	unique(mac_address, pin),	
	foreign key (type_id) references device_types(id),
	foreign key (scale_unit_id) references units(id),
	foreign key (user_id) references users(id)
);
comment on table devices                    is 'Устройства';
comment on column devices.id                is 'Идентификатор устройства';
comment on column devices.type_id           is 'Вид устройства';
comment on column devices.mac_address       is 'MAC адрес устройства';
comment on column devices.serial_number     is 'Серийный номер устройства';
comment on column devices.scale_unit_id     is 'Единица измерения шкалы';
comment on column devices.step_increment    is 'Шаг увеличения';
comment on column devices.indicator         is 'Текущее значение счетчика';
comment on column devices.user_id           is 'Пользователь счетчика';
comment on column devices.state             is 'Статус устройства';