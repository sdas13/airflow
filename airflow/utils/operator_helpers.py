#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
from typing import Callable, Dict, List, Tuple, Union

AIRFLOW_VAR_NAME_FORMAT_MAPPING = {
    'AIRFLOW_CONTEXT_DAG_ID': {'default': 'airflow.ctx.dag_id', 'env_var_format': 'AIRFLOW_CTX_DAG_ID'},
    'AIRFLOW_CONTEXT_TASK_ID': {'default': 'airflow.ctx.task_id', 'env_var_format': 'AIRFLOW_CTX_TASK_ID'},
    'AIRFLOW_CONTEXT_EXECUTION_DATE': {
        'default': 'airflow.ctx.execution_date',
        'env_var_format': 'AIRFLOW_CTX_EXECUTION_DATE',
    },
    'AIRFLOW_CONTEXT_DAG_RUN_ID': {
        'default': 'airflow.ctx.dag_run_id',
        'env_var_format': 'AIRFLOW_CTX_DAG_RUN_ID',
    },
    'AIRFLOW_CONTEXT_DAG_OWNER': {
        'default': 'airflow.ctx.dag_owner',
        'env_var_format': 'AIRFLOW_CTX_DAG_OWNER',
    },
    'AIRFLOW_CONTEXT_DAG_EMAIL': {
        'default': 'airflow.ctx.dag_email',
        'env_var_format': 'AIRFLOW_CTX_DAG_EMAIL',
    },
}


def context_to_airflow_vars(context, in_env_var_format=False):
    """
    Given a context, this function provides a dictionary of values that can be used to
    externally reconstruct relations between dags, dag_runs, tasks and task_instances.
    Default to abc.def.ghi format and can be made to ABC_DEF_GHI format if
    in_env_var_format is set to True.

    :param context: The context for the task_instance of interest.
    :type context: dict
    :param in_env_var_format: If returned vars should be in ABC_DEF_GHI format.
    :type in_env_var_format: bool
    :return: task_instance context as dict.
    """
    params = {}
    if in_env_var_format:
        name_format = 'env_var_format'
    else:
        name_format = 'default'
    task = context.get('task')
    if task and task.email:
        if isinstance(task.email, str):
            params[AIRFLOW_VAR_NAME_FORMAT_MAPPING['AIRFLOW_CONTEXT_DAG_EMAIL'][name_format]] = task.email
        elif isinstance(task.email, list):
            # os env variable value needs to be string
            params[AIRFLOW_VAR_NAME_FORMAT_MAPPING['AIRFLOW_CONTEXT_DAG_EMAIL'][name_format]] = ','.join(
                task.email
            )
    if task and task.owner:
        if isinstance(task.owner, str):
            params[AIRFLOW_VAR_NAME_FORMAT_MAPPING['AIRFLOW_CONTEXT_DAG_OWNER'][name_format]] = task.owner
        elif isinstance(task.owner, list):
            # os env variable value needs to be string
            params[AIRFLOW_VAR_NAME_FORMAT_MAPPING['AIRFLOW_CONTEXT_DAG_OWNER'][name_format]] = ','.join(
                task.owner
            )
    task_instance = context.get('task_instance')
    if task_instance and task_instance.dag_id:
        params[AIRFLOW_VAR_NAME_FORMAT_MAPPING['AIRFLOW_CONTEXT_DAG_ID'][name_format]] = task_instance.dag_id
    if task_instance and task_instance.task_id:
        params[
            AIRFLOW_VAR_NAME_FORMAT_MAPPING['AIRFLOW_CONTEXT_TASK_ID'][name_format]
        ] = task_instance.task_id
    if task_instance and task_instance.execution_date:
        params[
            AIRFLOW_VAR_NAME_FORMAT_MAPPING['AIRFLOW_CONTEXT_EXECUTION_DATE'][name_format]
        ] = task_instance.execution_date.isoformat()
    dag_run = context.get('dag_run')
    if dag_run and dag_run.run_id:
        params[AIRFLOW_VAR_NAME_FORMAT_MAPPING['AIRFLOW_CONTEXT_DAG_RUN_ID'][name_format]] = dag_run.run_id
    return params


def determine_kwargs(func: Callable, args: Union[Tuple, List], kwargs: Dict) -> Dict:
    """
    Inspect the signature of a given callable to determine which arguments in kwargs need
    to be passed to the callable.

    :param func: The callable that you want to invoke
    :param args: The positional arguments that needs to be passed to the callable, so we
        know how many to skip.
    :param kwargs: The keyword arguments that need to be filtered before passing to the callable.
    :return: A dictionary which contains the keyword arguments that are compatible with the callable.
    """
    import inspect
    import itertools

    signature = inspect.signature(func)
    has_kwargs = any(p.kind == p.VAR_KEYWORD for p in signature.parameters.values())

    for name in itertools.islice(signature.parameters.keys(), len(args)):
        # Check if args conflict with names in kwargs
        if name in kwargs:
            raise ValueError(f"The key {name} in args is part of kwargs and therefore reserved.")

    if has_kwargs:
        # If the callable has a **kwargs argument, it's ready to accept all the kwargs.
        return kwargs

    # If the callable has no **kwargs argument, it only wants the arguments it requested.
    return {key: kwargs[key] for key in signature.parameters if key in kwargs}


def make_kwargs_callable(func: Callable) -> Callable:
    """
    Make a new callable that can accept any number of positional or keyword arguments
    but only forwards those required by the given callable func.
    """
    import functools

    @functools.wraps(func)
    def kwargs_func(*args, **kwargs):
        kwargs = determine_kwargs(func, args, kwargs)
        return func(*args, **kwargs)

    return kwargs_func
