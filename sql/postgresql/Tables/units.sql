create table units
(
	id		serial primary key,
	name	varchar(100) not null,
	si_code	varchar(100) not null,
	unique (name),
	unique (si_code)
)