-- Изменение пользователя
create or replace procedure change_password(
	p_user_id	integer,
    p_psw      	varchar
)
as $$
begin
	update
		users 
	set 
		psw = md5(p_psw)
	where 
		id = p_user_id;
end;
$$ language plpgsql SECURITY DEFINER;