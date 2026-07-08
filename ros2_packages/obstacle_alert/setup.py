from setuptools import setup
package_name = 'obstacle_alert'
setup(
    name=package_name, version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='rock', maintainer_email='rock@todo.todo',
    description='Obstacle Alert',
    license='MIT',
    entry_points={
        'console_scripts': ['obstacle_alert = obstacle_alert.obstacle_alert_node:main'],
    },
)