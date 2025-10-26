create table roles
(
	id      serial primary key,     -- Идентификатор
	name    varchar(100) not null,  -- Название роли
	code    varchar(100) not null,  -- Код роли
	state   boolean not null,       -- Статус (удален не удален)
	unique (name),
	unique (code)
);
comment on table roles           is 'Роли';
comment on column roles.id       is 'Идентификатор роли';
comment on column roles.name     is 'Название роли';
comment on column roles.code     is 'Код роли';
comment on column roles.state    is 'Статус роли';