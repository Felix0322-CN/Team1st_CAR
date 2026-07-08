from setuptools import setup
package_name = 'wechat_control'
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
    description='MQTT Bridge for WeChat Control',
    license='MIT',
    entry_points={
        'console_scripts': ['mqtt_bridge = wechat_control.mqtt_bridge_node:main'],
    },
)