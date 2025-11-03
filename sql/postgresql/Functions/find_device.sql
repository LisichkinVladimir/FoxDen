create or replace function find_device(p_mac_address varchar, p_pin integer default null) returns integer 
as $$
declare
	v_result integer;
begin
	select id into v_result
	from public.devices
	where mac_address = p_mac_address
	  and pin = coalesce(p_pin, pin)
	  and state = true;
	return v_result;  
end;
$$ language plpgsql SECURITY DEFINER;
