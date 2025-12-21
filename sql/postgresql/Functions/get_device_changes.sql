create or replace function get_device_changes(p_device_id integer) RETURNS 
TABLE
(
	moment timestamp with time zone
) 
as $$
declare
	v_result integer;
begin
	return query
	select t.moment 
	from device_changes t
	where t.device_id = p_device_id 
	order by t.moment asc;
end;
$$ language plpgsql SECURITY DEFINER;
