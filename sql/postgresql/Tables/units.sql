create table units
(
	id      serial primary key,	    -- Идентификатор
	name    varchar(100) not null,  -- Название еденицы измерения
	si_code varchar(100) not null,	-- Код в еденицах СИ
	unique (name),
	unique (si_code)
);
comment on table units           is 'Еденицы измерения';
comment on column units.id       is 'Идентификатор еденицы измерения';
comment on column units.name     is 'Название еденицы измерения';
comment on column units.si_code  is 'Код в еденицах СИ';
