create or replace function get_devices(p_user_id integer) returns 
table
(
	like devices
) 
as $$
begin
	return query
	select t.*
	from public.devices t
	where t.user_id = p_user_id
	order by t.serial_number;
end;
$$ language plpgsql SECURITY DEFINER;
