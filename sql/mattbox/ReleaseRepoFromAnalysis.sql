DELIMITER /MANGINA/
create or replace procedure `w3hacknet`.`ReleaseRepoFromAnalysis` (
IN _repo_id int(11),
IN _success bit(1),
IN _stats_json longblob,
IN _error_message varchar(256),
IN _timed_out bit(1)
)
BEGIN
	declare dt datetime default current_timestamp(3);
	declare _hacker_extension_map longblob;
	declare _hacker_name_map longblob;
	declare _repo_extension_map longblob;
	declare _repo_import_map longblob;
	declare _language_map longblob;
	declare _import_map longblob;
	declare _keys longblob;
	declare idx int default 0;
	declare _array_size int default 0;
	declare _key char(40);
	declare _val varchar(128);
	declare _email_key varchar(256);
	declare _md5 char(32);
	declare _alias_pk int;
	declare _extension_set longblob;
	declare _extension_keys longblob;
	declare _extension_len int;
	declare _ext_idx int default 0;
	declare _import_set longblob;
	declare _import_keys longblob;
	declare _import_key varchar(256);
	declare _import_len int;
	declare _imp_idx int default 0;
	declare _import_count int;
	declare _import_val varchar(256);
	declare _extension_val varchar(64);
	declare _extension_count int;
	declare _count int;
	declare _import_sub_map longblob;
	declare _hacker_contributions float;
	declare _hacker_cont_keys longblob;
	declare _hacker_cont_keys_len int;
	declare _hacker_cont_idx int;
	declare _hacker_md5 char(40);
	declare _contributor_map longblob;
	declare _contrib_hash_array longblob;
	declare _contrib_array_len int;
	declare _contrib_idx int;
	declare _contributor_hash char(40);
	declare _hacker_contrib_pct_map longblob;
	declare _hacker_hash_array longblob;
	declare _hacker_hash_len int;
	declare _hacker_idx int;
	declare _hacker_hash char(32);
	declare _hacker_pct varchar(32);
	declare _perf_track_id int;

	
	update repo set last_analysis_date = dt, failed_date = case when _success then null else dt end
	 where id = _repo_id;
	update repo_reserve set tstamp = dt where repo_id = _repo_id;	
	select LAST_INSERT_ID() into _perf_track_id; 
	select json_query(_stats_json, '$.hacker_extension_map') into _hacker_extension_map;


	select json_query(_stats_json, '$.hacker_name_map') into _hacker_name_map;
	select json_query(_stats_json, '$.extension_map') into _repo_extension_map;
	select json_query(_stats_json, '$.import_map_map') into _repo_import_map;
	select json_keys(_hacker_name_map) into _keys;

	select json_length(_keys) into _array_size;

	set idx = 0;
	while idx < _array_size do
		select json_value(_keys, concat('$[', idx, ']')) into _md5;

		select json_value(_hacker_name_map, concat('$.', _md5)) into _email_key;

		insert into hacker_update_queue (md5, name_email) select _md5, _email_key;
		select id into _alias_pk from alias where md5 = _md5;
		select json_query(_hacker_extension_map, concat('$.', _md5)) into _extension_set;
		select json_keys(_extension_set) into _extension_keys;
		select json_length(_extension_keys) into _extension_len;
		set _ext_idx = 0;
		while _ext_idx < _extension_len do
			select json_value(_extension_keys, concat('$[', _ext_idx, ']')) into _extension_val;
			select json_value(_extension_set, concat('$.', _extension_val)) into _extension_count;

			call UpdateHackerExtensionCount(_alias_pk, _extension_val, _extension_count);
			set _ext_idx = _ext_idx + 1;
		end while;
		set idx = idx + 1;
	end while;		

	select json_keys(_repo_extension_map) into _keys;
	select json_length(_keys) into _array_size;
	set idx = 0;
	while idx < _array_size do
		select json_value(_keys, concat('$[', idx, ']')) into _key;
		select json_value(_repo_extension_map, concat('$.', _key)) into _count;

		call UpdateRepoExtensionCount(_repo_id, _key, _count);
		set idx = idx + 1;
	end while;	
	
	select json_keys(_repo_import_map) into _keys;  
	select json_length(_keys) into _array_size; 	

	set idx = 0;
	while idx < _array_size do
		select json_value(_keys, concat('$[', idx, ']')) into _extension_val;

	    
		select json_query(_repo_import_map, concat('$.', _extension_val)) into _language_map;
		
		select json_query(_language_map, '$.contributors') into _contributor_map;
		select json_query(_language_map, '$.imports') into _import_map;
	
		select json_keys(_import_map) into _import_keys;
		select json_length(_import_keys) into _import_len;

		set _imp_idx = 0;
		while _imp_idx < _import_len do
			select json_value(_import_keys, concat('$[', _imp_idx, ']')) into _import_key;

			
			
			select json_query(_import_map, concat('$."', _import_key, '"')) into _contrib_hash_array;
			select json_length(_contrib_hash_array) into _contrib_array_len;
			set _contrib_idx = 0;
			while _contrib_idx < _contrib_array_len do
				call UpdateRepoImportCount(_repo_id, _import_key, _extension_val, 1);
				select json_value(_contrib_hash_array, concat('$[', _contrib_idx, ']')) into _contributor_hash;
				select json_query(_contributor_map, concat('$."', _contributor_hash, '"')) into _hacker_contrib_pct_map;

				select json_keys(_hacker_contrib_pct_map) into _hacker_hash_array;
				select json_length(_hacker_hash_array) into _hacker_hash_len;
				set _hacker_idx = 0;
				while _hacker_idx < _hacker_hash_len do
					select json_value(_hacker_hash_array, concat('$[', _hacker_idx, ']')) into _hacker_hash;

					select json_value(_hacker_contrib_pct_map, concat('$."', _hacker_hash, '"')) into _hacker_pct;

					call UpdateHackerImportCount(_hacker_hash, _import_key, _extension_val, cast(_hacker_pct as float));				
					set _hacker_idx = _hacker_idx + 1;
				end while;
				set _contrib_idx = _contrib_idx + 1;
			end while;
		
			set _imp_idx = _imp_idx + 1;
		end while;
		set idx = idx + 1;
	end while;

END
/MANGINA/
DELIMITER ;
