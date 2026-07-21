{# Par defaut, dbt prefixe le schema custom avec le schema cible
   (BRONZE_staging, BRONZE_silver, BRONZE_gold). On le surcharge pour
   avoir des schemas nommes directement STAGING, SILVER, GOLD. #}
{% macro generate_schema_name(custom_schema_name, node) -%}

    {%- set default_schema = target.schema -%}
    {%- if custom_schema_name is none -%}

        {{ default_schema }}

    {%- else -%}

        {{ custom_schema_name | trim }}

    {%- endif -%}

{%- endmacro %}
