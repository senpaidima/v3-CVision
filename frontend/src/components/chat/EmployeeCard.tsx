import React from "react";
import { Link } from "react-router-dom";
import { Employee } from "../../hooks/useStreamingSearch";
import "./EmployeeCard.css";

interface EmployeeCardProps {
  employee: Employee;
}

const EmployeeCard: React.FC<EmployeeCardProps> = ({ employee }) => {
  return (
    <Link
      to={`/employee/${employee.alias}`}
      className="employee-card"
      data-testid="employee-card"
    >
      <div className="employee-info">
        <h3 className="employee-name">{employee.name}</h3>
        <p className="employee-title">{employee.title}</p>
      </div>
      <div className="employee-alias">@{employee.alias}</div>
    </Link>
  );
};

export default EmployeeCard;
