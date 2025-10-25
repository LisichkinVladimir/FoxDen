create table divice_types
(
	id		serial primary key,
	name	varchar(100) not null,
	code	varchar(100) not null,
	state 	boolean,
	unique (name),
	unique (code)
)