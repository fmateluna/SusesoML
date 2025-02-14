-- SQLBook: Code
select
	min(ps.fecha_emision) as fecha_inicio,
	max(ps.fecha_emision) as fecha_fin
from
	lme.df_propensity_score as ps
where
	 ps.fecha_emision between :fecha_inicio and :fecha_fin
