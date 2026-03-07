create or replace function add_device(
	p_type_id			integer,
    p_mac_address		varchar,
    p_pin     			integer,
    p_serial_number		varchar,
	p_scale_unit_id		integer,
	p_step_increment	numeric,
	p_indicator			numeric,
	p_user_id			integer,
	p_state				boolean
) returns integer 
as $$
declare
	v_device_id   integer;
begin
	perform 1 from devices where mac_address = p_mac_address and pin = p_pin limit 1;
	if FOUND then
		RAISE NOTICE 'Устройство с указаным MAC адресом %, pin %, уже существует', p_mac_address, p_pin;
	else
		insert into devices (type_id, mac_address, pin, serial_number,
						   scale_unit_id, step_increment, indicator, user_id, state)
		values (p_type_id, p_mac_address, p_pin, p_serial_number,
			   p_scale_unit_id, p_step_increment, p_indicator, p_user_id, p_state)
		returning id into v_device_id;
		return v_device_id;
	end if;
end;
$$ language plpgsql SECURITY DEFINER;
