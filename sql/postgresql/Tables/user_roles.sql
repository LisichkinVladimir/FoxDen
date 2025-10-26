create table user_roles
(
	user_id	integer not null,       -- Идентификатор пользователя
	role_id	integer not null,       -- Идентификатор роли
	primary key (user_id, role_id),
	foreign key (user_id) references users(id),
	foreign key (role_id) references roles(id)
);
comment on table user_roles             is 'Роли пользователей';
comment on column user_roles.user_id    is 'Идентификатор пользователя';
comment on column user_roles.role_id    is 'Идентификатор роли';
