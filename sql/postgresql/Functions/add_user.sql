create or replace function add_user(
    p_name      varchar,
    p_email     varchar,
    p_surname   varchar,
	p_psw       varchar,
	p_state		boolean,
	p_roles     integer[] DEFAULT ARRAY[]::integer[]
) returns integer 
as $$
declare
	v_user_id   integer;
	v_role_id   integer;
begin
	perform 1 from users where name = p_name or email = p_email limit 1;
	if FOUND then
		RAISE NOTICE 'Пользователь с указаным именем % или email %, уже существует', p_name, p_email;
	else
		insert into public.users (name, email, surname, psw, state)
		values (p_name, p_email, p_surname, MD5(p_psw), true)
		returning id into v_user_id;
		-----------------
		foreach v_role_id in array p_roles loop
			insert into public.user_roles (user_id, role_id)
			values (v_user_id, v_role_id);
		end loop;
		return v_user_id;
	end if;
end;
$$ language plpgsql SECURITY DEFINER;
