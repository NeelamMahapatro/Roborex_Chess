//Don't make unknown changes
#include "MainUI.h"
#include <QApplication>
#include <iostream>
using namespace std;
int main(int argc, char *argv[])
{		
    ros::init(argc, argv, "chess_ui");
    ros::NodeHandle nh;
    QApplication a(argc, argv);
    MainUI w(nh);
    w.show();
    ros::Rate rate(30);
    while(ros::ok() && w.isVisible())
    {
        ros::spinOnce();
        rate.sleep();
        a.processEvents();
    }
    return 0;
}