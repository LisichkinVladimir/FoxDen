create table devices
(
	id		serial primary key,
	type_id integer,
	mac_adress varchar(12) not null,
	serial_number varchar(100) not null,
	scale_unit_id integer,
	step_increment integer,
	indicator numeric(8, 3),
	user_id integer,
	stale bool,
	foreign key (user_id) references users(id),
	foreign key (type_id) references device_types(id),
	foreign key (scale_unit_id) references units(id)
)
