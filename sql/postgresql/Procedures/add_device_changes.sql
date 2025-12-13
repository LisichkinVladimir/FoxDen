create or replace procedure add_device_changes(
    p_mac_address   varchar,
    p_device_id     integer,
	p_moment        timestamp with time zone
)
as $$
declare
	v_id integer;
begin
	select
		id
	into v_id
	from
		public.devices
	where
		mac_address = p_mac_address
		and id = p_device_id;
	if not found then
        raise notice 'device not found.';
    end if;
	insert into public.device_changes (device_id, moment)
	values (p_device_id, p_moment);
	------------
	update public.devices set
		"indicator" = "indicator" + "step_increment"
	where id = v_id;
end;
$$ language plpgsql SECURITY DEFINER;