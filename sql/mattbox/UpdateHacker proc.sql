CREATE DEFINER=`matt`@`localhost` PROCEDURE `w3hacknet`.`UpdateHacker`(
in _md5 char(32),
in _name_email varchar(256),
in _commit_count int,
in _min_date datetime,
in _max_date datetime,
in _commit_array json
)
BEGIN
	declare _alias_id int default null;
	declare _commit_count int default 0;
	declare _commit_array_size int default 0;
	declare _commit json;
	declare _commit_key_idx int default 0;
	declare _commit_id char(40);

	if exists (select id from alias a where a.md5 = _md5) THEN 
		select id into _alias_id from alias a where a.md5 = _md5;
		update alias set count = count + _commit_count where id = _alias_id;
	else
		insert into alias (md5, name, count) values (_md5, _name_email, _commit_count);
		select LAST_INSERT_ID() into _alias_id;
		call debug(concat('New alias id is ', _alias_id));
	end if;
	
	if exists (select * from alias a where a.id = _alias_id and a.github_user_id is null) THEN 
		select count(*) into _commit_count from commit c where c.alias_id = _alias_id;
		if _commit_count < 3 then
			set _commit_array_size = json_length(_commit_array);
			if _commit_array_size > _commit_count then
				set _commit_key_idx = 0;
				while _commit_key_idx < json_length(_commit_array) DO
					set _commit = json_query(_commit_array, concat('$[',_commit_key_idx,']'));
					select json_value(_commit, '$.cid') into _commit_id;
					if exists(select id from commit where commit_id = _commit_id) THEN 
						if exists(select * from alias where id = _alias_id and github_user_id is null) and 
						   exists(select * from commit c join alias a on a.id = c.alias_id where c.commit_id = _commit_id and github_user_id is not null) THEN 
						   /* Okay - does this *new* record still not have a github_user_id, 
						    * *and* does the pre-existing commit record point to an alias that *does* have a github user Id
						    * If all this is true, then copy the github user id.  Yikes!
						    */
						   call debug(concat('Found an alternative ID for ', _md5, _name_email, _commit_key_idx));
							update alias set github_user_id = (select a.github_user_id from commit c join alias a on a.id = c.alias_id where c.commit_id = _commit_id)
								where id = _alias_id;
						end if;
					else
						insert into commit(commit_id, alias_id, date, gmt_offset)
						 select _commit_id, _alias_id, FROM_UNIXTIME(json_value(_commit, '$.dt')), json_value(_commit, '$.tz');
					end if;
					set _commit_key_idx = _commit_key_idx + 1;
				end while;
			end if;
		end if;
	end if;
END