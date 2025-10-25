create table users
(
	id		serial primary key,
	name	varchar(100) not null,
	email	varchar(320) not null,
	surname varchar(1000) not null,
	psw		varchar(1000) not null,
	state	bool,
	unique(email),
	unique(name)
)
