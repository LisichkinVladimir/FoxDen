create or replace function find_device(p_mac_address varchar) returns integer 
as $$
declare
	v_result integer;
begin
	select id into v_result
	from public.devices
	where mac_address = p_mac_address
	  and state = true;
	return v_result;  
end;
$$ language plpgsql SECURITY DEFINER;
