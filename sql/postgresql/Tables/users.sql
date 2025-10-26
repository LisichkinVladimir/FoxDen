create table users
(
	id      serial primary key,     -- Идентификатор
	name    varchar(100) not null,  -- Короткое имя пользователя
	email   varchar(320) not null,  -- EMail пользователя
	surname varchar(1000) not null, -- Полное имя пользователя
	psw     varchar(1000) not null, -- Пароль пользователя
	state   bool not null,          -- Статус (удален не удален)
	unique(email),
	unique(name)
);
comment on table users           is 'Пользователи';
comment on column users.id       is 'Идентификатор пользователч';
comment on column users.name     is 'Короткое имя пользователя';
comment on column users.email    is 'EMail пользователя';
comment on column users.surname  is 'Полное имя пользователя';
comment on column users.psw      is 'Пароль пользователя';
comment on column users.state    is 'Статус пользователя';