GRANT EXECUTE ON FUNCTION public.find_device(character varying, integer) TO foxden_user;
GRANT EXECUTE ON FUNCTION public.get_user(character varying, character varying) TO foxden_user;
GRANT EXECUTE ON FUNCTION public.get_device_changes(integer) TO foxden_user;
GRANT EXECUTE ON PROCEDURE public.add_device_changes(character varying, integer, timestamp with time zone) TO foxden_user;
