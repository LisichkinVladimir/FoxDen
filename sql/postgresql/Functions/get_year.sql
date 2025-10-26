create function get_year(p_date timestamp with time zone) returns integer
as $$
begin
    return extract(year from p_date);
end;
$$ language plpgsql immutable;