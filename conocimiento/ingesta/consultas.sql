-- Solo lectura; ejecutar sobre conocimiento/datos/biblioteca.sqlite.
-- N170 B1, H=1,5, c13: tabla del historial con una consulta.
SELECT muestreo,
       max(CASE WHEN evaluacion='GX' THEN valor END) AS GX,
       max(CASE WHEN evaluacion='LP_max' THEN valor END) AS LP_max
FROM medida_cmm
WHERE pieza='3212' AND cota='170' AND bolt='B1' AND altura=1.5 AND cavidad='c13'
GROUP BY muestreo ORDER BY muestreo;

-- LP máximo: no mezclarlo con GX ni con alturas/cavidades omitidas.
SELECT muestreo,count(*) AS evaluados,
       sum(valor<nominal+tol_inf-1e-9 OR valor>nominal+tol_sup+1e-9) AS fuera
FROM medida_cmm WHERE pieza='3212' AND cota='170' AND evaluacion='LP_max'
GROUP BY muestreo ORDER BY muestreo;
