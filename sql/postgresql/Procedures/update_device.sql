-- Изменение устройства
create or replace procedure update_device(
	p_device_id			integer,
	p_type_id			integer,
    p_mac_address		varchar,
    p_pin     			integer,
    p_serial_number		varchar,
	p_scale_unit_id		integer,
	p_step_increment	numeric,
	p_indicator			numeric,
	p_state				boolean
)
as $$
begin
	perform 1 from devices where id <> p_device_id and mac_address = p_mac_address and pin = p_pin limit 1;
	if FOUND then
		RAISE NOTICE 'Устройство с указаным MAC адресом %, pin %, уже существует', p_mac_address, p_pin;
	else
		update 
			devices 
		set 
			type_id = p_type_id,
			mac_address = p_mac_address, 
			pin = p_pin,
			serial_number = p_serial_number, 
			scale_unit_id = p_scale_unit_id,
			step_increment = p_step_increment, 
			indicator = p_indicator,
			state = p_state
		where id = p_device_id;
	end if;
end;
$$ language plpgsql SECURITY DEFINER;