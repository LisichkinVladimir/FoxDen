create or replace function get_user(p_name varchar, p_password varchar) returns 
table
(
	like users
) 
as $$
begin
	return query
	select t.*
	from public.users t
	where t.name = p_name
	  and t.psw = md5(p_password)
	  and t.state = true;
end;
$$ language plpgsql SECURITY DEFINER;
