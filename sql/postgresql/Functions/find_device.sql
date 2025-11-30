create or replace function find_device(p_mac_address varchar, p_pin integer default null) RETURNS 
TABLE
(
	id integer, 
	pin integer
) 
as $$
declare
	v_result integer;
begin
	return query
	select t.id, t.pin
	from public.devices t
	where t.mac_address = p_mac_address
	  and t.pin = coalesce(p_pin, t.pin)
	  and t.state = true;
end;
$$ language plpgsql SECURITY DEFINER;
