create or replace function is_admin(p_user_id integer) returns integer 
as $$
declare
	v_count	integer;
begin
	select count(*) into v_count
	from user_roles ur
	join roles r on ur.role_id = r.id
	where ur.user_id = p_user_id 
	  and r.code = 'administrator'
	  and r.state = true;
	return v_count;
end;
$$ language plpgsql SECURITY DEFINER;
