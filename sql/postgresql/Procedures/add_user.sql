-- Добавление нового пользователя
create or replace procedure add_user(
    p_name      varchar,
    p_email     varchar,
    p_surname   varchar,
	p_psw       varchar,
	p_roles     integer[]
)
language plpgsql
as $$
declare
	v_user_id   integer;
	v_role_id   integer;
begin
	insert into public.users (name, email, surname, psw, state)
	values (p_name, p_email, p_surname, MD5(p_psw), true)
	returning id into v_user_id;
	-----------------
	foreach v_role_id in array p_roles loop
		insert into public.user_roles (user_id, role_id)
		values (v_user_id, v_role_id);
	end loop;
end;
$$;