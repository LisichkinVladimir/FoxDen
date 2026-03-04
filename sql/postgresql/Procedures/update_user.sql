-- Изменение пользователя
create or replace procedure update_user(
	user_id		integer,
    p_name      varchar,
    p_email     varchar,
    p_surname   varchar,
	p_state		boolean
)
as $$
begin
	update
		users 
	set 
		name = p_name, 
		email = p_email, 
		surname = p_surname, 
		state = p_state
	where 
		id = p_user_id;
end;
$$ language plpgsql SECURITY DEFINER;