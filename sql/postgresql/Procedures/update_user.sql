-- Изменение пользователя
create or replace procedure update_user(
	p_user_id	integer,
    p_name      varchar,
    p_email     varchar,
    p_surname   varchar,
	p_state		boolean
)
as $$
begin
	perform 1 from users where id <> p_user_id and (name = p_name or email = p_email) limit 1;
	if FOUND then
		RAISE NOTICE 'Пользователь с указаным именем % или email %, уже существует', p_name, p_email;
	else
		update
			users 
		set 
			name = p_name, 
			email = p_email, 
			surname = p_surname, 
			state = p_state
		where 
			id = p_user_id;
	end if;
end;
$$ language plpgsql SECURITY DEFINER;